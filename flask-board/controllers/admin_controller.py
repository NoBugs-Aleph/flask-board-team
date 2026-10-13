"""관리자 전용 회원 관리 API."""
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request

from controllers.authz import api_role_required, current_user
from controllers.gelf import request_src_ip, send_gelf
from controllers.seclog import write_auth_fail
from controllers.pagination import SortError, paginate
from extensions import db
from models import (
    ROLE_ADMIN,
    ROLE_GOLD,
    ROLE_USER,
    VALID_ROLES,
    BlockedIP,
    Incident,
    Post,
    SecurityEvent,
    User,
    role_name,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

ROLE_ALIASES = {
    "user": ROLE_USER,
    "gold": ROLE_GOLD,
    "admin": ROLE_ADMIN,
    "0": ROLE_USER,
    "1": ROLE_GOLD,
    "2": ROLE_ADMIN,
}


def _admin_count(exclude_user_id=None):
    query = User.query.filter(User.role >= ROLE_ADMIN)
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.count()


def _admin_or_api_key_required(view):
    """관리자 JWT 또는 n8n용 관리자 API 키 중 하나를 요구한다."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        expected_key = current_app.config.get("ADMIN_API_KEY", "")
        supplied_key = request.headers.get("X-API-Key", "")
        if expected_key and supplied_key == expected_key:
            g.security_actor = "apikey"
            return view(*args, **kwargs)
        if supplied_key:
            write_auth_fail(request_src_ip(), request.path[:120])
            # S6: 키를 내밀었는데 틀렸다 = 추측 시도. 관리자 화면(쿠키 로그인)은
            # 키를 보내지 않으므로 여기에 걸리지 않는다. 키 값은 남기지 않는다.
            send_gelf(
                f"admin api auth failed {request.path[:80]}",
                rule="admin-auth-fail",
                src_ip=request_src_ip(),
                path=request.path[:120],
                code=401,
            )

        user = current_user()
        if user is None:
            return (
                jsonify(
                    {
                        "msg": "로그인이 필요합니다.",
                        "reason": "unauthenticated",
                        "required_role": ROLE_ADMIN,
                        "required_role_name": role_name(ROLE_ADMIN),
                        "current_role": None,
                    }
                ),
                401,
            )
        if not user.is_admin:
            return (
                jsonify(
                    {
                        "msg": "관리자 등급 이상만 접근할 수 있습니다.",
                        "reason": "insufficient_role",
                        "required_role": ROLE_ADMIN,
                        "required_role_name": role_name(ROLE_ADMIN),
                        "current_role": user.role,
                    }
                ),
                403,
            )
        g.security_actor = user.username
        return view(*args, **kwargs)

    return wrapper


def _security_actor():
    return getattr(g, "security_actor", "unknown")


def _as_nonnegative_int(value, field_name, default=0):
    if value in (None, ""):
        return default, None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None, f"{field_name}은 숫자여야 합니다."
    if parsed < 0:
        return None, f"{field_name}은 0 이상이어야 합니다."
    return parsed, None


def _role_value(value):
    if isinstance(value, int) and value in VALID_ROLES:
        return value
    return ROLE_ALIASES.get(str(value or "").strip().lower())


def _allowlist(value=None):
    if value:
        return [username.strip() for username in value.split(",") if username.strip()]
    return current_app.config.get("ADMIN_ALLOWLIST", [])


_BULK_MAX = 500
_PROTECTED_USERS = ("soarbot",)
_USER_SORTS = {name: getattr(User, name) for name in (
    "id", "username", "role", "is_locked", "locked_at", "failed_logins",
)}


def _parse_ids(data):
    ids = data.get("ids") if isinstance(data, dict) else None
    if (isinstance(ids, list) and 0 < len(ids) <= _BULK_MAX
            and all(type(value) is int and value > 0 for value in ids)):
        return set(ids)
    return None


def _user_filters(query, source):
    term = str(source.get("q") or "").strip()[:100]
    if term:
        query = query.filter(db.or_(
            User.username.contains(term, autoescape=True),
            User.role_granted_by.contains(term, autoescape=True),
            User.role_reason.contains(term, autoescape=True),
        ))
    requested_role = source.get("role")
    if requested_role not in (None, ""):
        role = _role_value(requested_role)
        if role is None:
            raise ValueError("role 값이 올바르지 않습니다.")
        query = query.filter_by(role=role)
    locked = str(source.get("locked", ""))
    if locked not in ("", "0", "1"):
        raise ValueError("locked는 0 또는 1이어야 합니다.")
    if locked:
        query = query.filter(User.is_locked.is_(locked == "1"))
    return query


def _bulk_targets(data):
    wanted = _parse_ids(data)
    if wanted is None:
        return None, None
    users = User.query.filter(User.id.in_(wanted)).order_by(User.id).all()
    return users, sorted(wanted - {user.id for user in users})


def _keep_last_admin(targets, locking=False):
    """여러 관리자를 한꺼번에 선택해도 마지막 한 명은 남긴다."""
    candidates = [user for user in targets if user.is_admin]
    if not candidates:
        return targets, []
    remaining = User.query.filter(User.role >= ROLE_ADMIN)
    if locking:
        remaining = remaining.filter(User.is_locked.is_(False))
    remaining = remaining.filter(User.id.notin_([user.id for user in targets]))
    if remaining.count():
        return targets, []
    survivor = min(candidates, key=lambda user: user.id)
    return [user for user in targets if user.id != survivor.id], [survivor.id]


def _user_audit(targets, reason, decision="deny"):
    if targets:
        db.session.add(SecurityEvent(
            student=_security_actor()[:50], src_ip=request_src_ip() or "0.0.0.0",
            fail_count=0, decision=decision, severity="Medium", reason=reason[:200],
            users=", ".join(sorted(user.username for user in targets))[:255],
            source="admin-console",
        ))


@admin_bp.get("/users")
@_admin_or_api_key_required
def list_users():
    """화면은 서버 페이징, page/per_page 없는 회수봇 호출은 전원 조회."""
    try:
        query = _user_filters(User.query, request.args)
        meta = {}
        if "page" in request.args or "per_page" in request.args:
            users, meta = paginate(query, request.args, _USER_SORTS, User.id, default_sort="role")
        else:
            users = query.order_by(User.role.desc(), User.id.asc()).all()
    except (ValueError, SortError) as error:
        return jsonify({"msg": str(error)}), 400
    post_counts = dict(
        db.session.query(Post.author_id, db.func.count(Post.id))
        .filter(Post.author_id.in_([user.id for user in users]))
        .group_by(Post.author_id)
        .all()
    )
    me = current_user()
    return jsonify(
        {
            "count": len(users),
            **meta,
            "summary": dict(db.session.query(User.role, db.func.count(User.id)).group_by(User.role).all()),
            "users": [
                {
                    **user.to_dict(),
                    "post_count": post_counts.get(user.id, 0),
                    "is_me": bool(me and user.id == me.id),
                }
                for user in users
            ],
            "roles": [
                {"value": value, "name": role_name(value)} for value in VALID_ROLES
            ],
            "me": me.to_dict() if me else None,
        }
    )


@admin_bp.post("/users/lock")
@_admin_or_api_key_required
def lock_users_bulk():
    data = request.get_json(silent=True)
    users, not_found = _bulk_targets(data)
    if users is None:
        return jsonify({"msg": f"ids(양의 정수 목록, 1~{_BULK_MAX}개)가 필요합니다."}), 400
    me = current_user()
    self_skipped = [user.id for user in users if me and user.id == me.id]
    skipped = [user.id for user in users if user.is_locked and user.id not in self_skipped]
    targets = [user for user in users if not user.is_locked and user.id not in self_skipped]
    targets, last_admin_skipped = _keep_last_admin(targets, locking=True)
    reason = str(data.get("reason") or f"관리자 수동 차단 by {_security_actor()}")[:200]
    now = datetime.now()
    for user in targets:
        user.is_locked, user.locked_at, user.lock_reason = True, now, reason
    _user_audit(targets, f"관리자 계정 차단 {len(targets)}건: {reason}")
    db.session.commit()
    changed = [user.id for user in targets]
    return jsonify(msg=f"{len(changed)}명 차단", count=len(changed), changed=changed,
                   skipped=skipped, not_found=not_found, self_skipped=self_skipped,
                   last_admin_skipped=last_admin_skipped, actor=_security_actor())


@admin_bp.post("/users/unlock")
@_admin_or_api_key_required
def unlock_users_bulk():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"msg": "JSON 객체가 필요합니다."}), 400
    if data.get("all_locked") is True:
        try:
            targets = _user_filters(User.query, data).filter(User.is_locked.is_(True)).order_by(User.id).all()
        except ValueError as error:
            return jsonify({"msg": str(error)}), 400
        skipped, not_found = [], []
    else:
        users, not_found = _bulk_targets(data)
        if users is None:
            return jsonify({"msg": f"ids(양의 정수 목록, 1~{_BULK_MAX}개) 또는 all_locked: true가 필요합니다."}), 400
        skipped = [user.id for user in users if not user.is_locked]
        targets = [user for user in users if user.is_locked]
    for user in targets:
        user.is_locked, user.failed_logins, user.lock_reason = False, 0, None
    _user_audit(targets, f"관리자 계정 차단 해제 {len(targets)}건", decision="allow")
    db.session.commit()
    changed = [user.id for user in targets]
    return jsonify(msg=f"{len(changed)}명 차단 해제", count=len(changed), changed=changed,
                   skipped=skipped, not_found=not_found, actor=_security_actor())


@admin_bp.post("/users/delete")
@_admin_or_api_key_required
def delete_users_bulk():
    data = request.get_json(silent=True)
    users, not_found = _bulk_targets(data)
    if users is None:
        return jsonify({"msg": f"ids(양의 정수 목록, 1~{_BULK_MAX}개)가 필요합니다."}), 400
    me = current_user()
    self_skipped = [user.id for user in users if me and user.id == me.id]
    protected = [user.id for user in users if user.username in _PROTECTED_USERS and user.id not in self_skipped]
    targets = [user for user in users if user.id not in self_skipped + protected]
    targets, last_admin_skipped = _keep_last_admin(targets)
    changed = [user.id for user in targets]
    posts_deleted = 0
    if targets:
        _user_audit(targets, f"관리자 회원 삭제 {len(targets)}명")
        posts_deleted = Post.query.filter(Post.author_id.in_(changed)).delete(synchronize_session=False)
        User.query.filter(User.id.in_(changed)).delete(synchronize_session=False)
    db.session.commit()
    return jsonify(msg=f"{len(changed)}명 삭제 (게시글 {posts_deleted}건 포함)", count=len(changed),
                   changed=changed, posts_deleted=posts_deleted, not_found=not_found,
                   self_skipped=self_skipped, protected=protected,
                   last_admin_skipped=last_admin_skipped, actor=_security_actor())


@admin_bp.patch("/users/<int:user_id>")
@api_role_required(ROLE_ADMIN)
def update_user(user_id):
    """회원 등급을 수정한다."""
    me = current_user()
    target = db.session.get(User, user_id)
    if target is None:
        return jsonify({"msg": "존재하지 않는 회원입니다."}), 404

    data = request.get_json(silent=True) or {}
    if "role" not in data:
        return jsonify({"msg": "role 값이 필요합니다."}), 400
    try:
        new_role = int(data["role"])
    except (TypeError, ValueError):
        return jsonify({"msg": "role은 숫자여야 합니다."}), 400
    if new_role not in VALID_ROLES:
        return jsonify({"msg": f"role은 {list(VALID_ROLES)} 중 하나여야 합니다."}), 400

    # 스스로 강등해 관리자 화면에서 잠기는 사고를 막는다.
    if target.id == me.id and new_role < ROLE_ADMIN:
        return jsonify({"msg": "자기 자신의 등급은 내릴 수 없습니다."}), 400
    # 마지막 관리자가 사라지면 아무도 회원 관리를 할 수 없게 된다.
    if target.role >= ROLE_ADMIN and new_role < ROLE_ADMIN and _admin_count(target.id) == 0:
        return jsonify({"msg": "마지막 관리자는 강등할 수 없습니다."}), 400

    previous = target.role_name
    target.role = new_role
    target.role_granted_by = me.username
    target.role_granted_at = datetime.now()
    target.role_reason = str(data.get("reason") or "관리자 화면에서 등급 변경")[:200]
    db.session.commit()
    return jsonify(
        {
            "msg": f"{target.username}님의 등급을 {previous} → {target.role_name}(으)로 변경했습니다.",
            "user": target.to_dict(),
        }
    )


@admin_bp.delete("/users/<int:user_id>")
@api_role_required(ROLE_ADMIN)
def delete_user(user_id):
    """회원을 삭제한다. 남은 게시글도 함께 정리한다."""
    me = current_user()
    target = db.session.get(User, user_id)
    if target is None:
        return jsonify({"msg": "존재하지 않는 회원입니다."}), 404
    if target.id == me.id:
        return jsonify({"msg": "자기 자신은 삭제할 수 없습니다."}), 400
    if target.username in _PROTECTED_USERS:
        return jsonify({"msg": "시스템 계정은 삭제할 수 없습니다."}), 400
    if target.role >= ROLE_ADMIN and _admin_count(target.id) == 0:
        return jsonify({"msg": "마지막 관리자는 삭제할 수 없습니다."}), 400

    # 게시글은 author_id 외래키로 묶여 있어 먼저 지워야 한다.
    removed_posts = Post.query.filter_by(author_id=target.id).delete()
    username = target.username
    db.session.delete(target)
    db.session.commit()
    return jsonify(
        {"msg": f"{username}님을 삭제했습니다. (게시글 {removed_posts}건 함께 삭제)"}
    )


@admin_bp.get("/violations")
@_admin_or_api_key_required
def list_privilege_violations():
    """허용목록에 없는 관리자 계정을 자동 권한 감사용으로 반환한다."""
    allowed = _allowlist(request.args.get("allowlist"))
    admins = User.query.filter(User.role >= ROLE_ADMIN).order_by(User.id.asc()).all()
    violations = [user for user in admins if user.username not in allowed]
    return jsonify(
        {
            "allowlist": allowed,
            "count": len(violations),
            "violations": [user.to_dict() for user in violations],
        }
    )


@admin_bp.post("/grant")
@_admin_or_api_key_required
def grant_role():
    """아이디와 등급 이름 또는 숫자로 권한을 부여하는 자동화 호환 API."""
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    new_role = _role_value(data.get("role"))
    if not username or new_role is None:
        return jsonify({"msg": "username과 role(user|gold|admin 또는 0|1|2)이 필요합니다."}), 400
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({"msg": f"없는 사용자: {username}"}), 404

    me = current_user()
    if me and user.id == me.id and new_role < ROLE_ADMIN:
        return jsonify({"msg": "자기 자신의 등급은 내릴 수 없습니다."}), 400
    if (
        user.role >= ROLE_ADMIN
        and new_role < ROLE_ADMIN
        and _admin_count(user.id) == 0
    ):
        return jsonify({"msg": "마지막 관리자는 강등할 수 없습니다."}), 400

    old_role = user.role
    actor = _security_actor()
    user.role = new_role
    user.role_granted_by = actor
    user.role_granted_at = datetime.now()
    user.role_reason = str(data.get("reason") or "")[:200]
    db.session.commit()
    return jsonify(
        {
            "msg": "역할 부여 완료",
            "username": username,
            "old_role": old_role,
            "new_role": new_role,
            "old_role_name": role_name(old_role),
            "new_role_name": role_name(new_role),
            "granted_by": actor,
        }
    )


@admin_bp.post("/revoke")
@_admin_or_api_key_required
def revoke_role():
    """과잉권한을 일반 등급으로 회수하고 감사 이벤트를 남긴다."""
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    if not username:
        return jsonify({"msg": "username은 필수입니다."}), 400
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({"msg": f"없는 사용자: {username}"}), 404

    old_role = user.role
    if old_role == ROLE_USER:
        return jsonify(
            {
                "msg": "이미 일반 권한이라 회수가 필요하지 않습니다.",
                "username": username,
                "old_role": old_role,
                "new_role": ROLE_USER,
                "revoked": False,
            }
        )

    me = current_user()
    if me and user.id == me.id:
        return jsonify({"msg": "자기 자신의 등급은 내릴 수 없습니다."}), 400
    if user.role >= ROLE_ADMIN and _admin_count(user.id) == 0:
        return jsonify({"msg": "마지막 관리자는 강등할 수 없습니다."}), 400

    actor = _security_actor()
    reason = str(
        data.get("reason") or f"과잉권한 회수: {username} {old_role}→{ROLE_USER}"
    )[:200]
    user.role = ROLE_USER
    user.role_granted_by = actor
    user.role_granted_at = datetime.now()
    user.role_reason = reason
    event = SecurityEvent(
        student=str(data.get("student") or actor)[:50],
        src_ip=str(data.get("src_ip") or "0.0.0.0")[:45],
        fail_count=0,
        decision="deny",
        severity=str(data.get("severity") or "High")[:10],
        reason=reason,
        users=username[:255],
        source=str(data.get("source") or "privilege-guard")[:50],
        generated_at=data.get("generated_at"),
    )
    db.session.add(event)
    db.session.commit()
    return jsonify(
        {
            "msg": "권한 회수 완료",
            "username": username,
            "old_role": old_role,
            "new_role": ROLE_USER,
            "revoked": True,
            "event_id": event.id,
            "revoked_by": actor,
        }
    )


@admin_bp.post("/lock")
@_admin_or_api_key_required
def lock_account():
    """계정을 잠그고 보안 감사 이벤트를 남긴다."""
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    if not username:
        return jsonify({"msg": "username은 필수입니다."}), 400
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({"msg": f"없는 사용자: {username}"}), 404
    if user.is_locked:
        return jsonify(
            {
                "msg": "이미 잠긴 계정",
                "username": username,
                "locked": True,
                "changed": False,
            }
        )

    fail_count, error = _as_nonnegative_int(data.get("fail_count"), "fail_count")
    if error:
        return jsonify({"msg": error}), 400

    actor = _security_actor()
    user.is_locked = True
    user.locked_at = datetime.now()
    user.lock_reason = str(
        data.get("reason") or f"브루트포스 자동 잠금 by {actor}"
    )[:200]
    event = SecurityEvent(
        student=str(data.get("student") or actor)[:50],
        src_ip=str(data.get("src_ip") or "0.0.0.0")[:45],
        fail_count=fail_count,
        decision="deny",
        severity=str(data.get("severity") or "High")[:10],
        reason=str(data.get("reason") or f"계정 잠금: {username}")[:200],
        users=username[:255],
        source=str(data.get("source") or "login-guard")[:50],
        generated_at=data.get("generated_at"),
    )
    db.session.add(event)
    db.session.commit()
    return jsonify(
        {
            "msg": "계정 잠금 완료",
            "username": username,
            "locked": True,
            "changed": True,
            "event_id": event.id,
            "locked_by": actor,
        }
    )


@admin_bp.post("/unlock")
@_admin_or_api_key_required
def unlock_account():
    """계정 잠금을 해제하고 로그인 실패 횟수를 초기화한다."""
    data = request.get_json(silent=True) or {}
    username = str(data.get("username") or "").strip()
    if not username:
        return jsonify({"msg": "username은 필수입니다."}), 400
    user = User.query.filter_by(username=username).first()
    if user is None:
        return jsonify({"msg": f"없는 사용자: {username}"}), 404

    user.is_locked = False
    user.failed_logins = 0
    user.locked_at = None
    user.lock_reason = None
    db.session.commit()
    return jsonify(
        {
            "msg": "잠금 해제 완료",
            "username": username,
            "locked": False,
            "unlocked_by": _security_actor(),
        }
    )


@admin_bp.post("/block")
@_admin_or_api_key_required
def block_ip():
    """IP를 차단 목록에 넣고 보안 감사 이벤트를 남긴다."""
    data = request.get_json(silent=True) or {}
    ip = str(data.get("ip") or data.get("src_ip") or "").strip()
    if not ip:
        return jsonify({"msg": "ip 또는 src_ip는 필수입니다."}), 400
    if len(ip) > 45:
        return jsonify({"msg": "ip는 45자 이하여야 합니다."}), 400

    existing = db.session.get(BlockedIP, ip)
    if existing:
        return jsonify(
            {"msg": "이미 차단된 IP", "ip": ip, "blocked": True, "changed": False}
        )

    fail_count, error = _as_nonnegative_int(data.get("fail_count"), "fail_count")
    if error:
        return jsonify({"msg": error}), 400

    actor = _security_actor()
    row = BlockedIP(
        ip=ip,
        reason=str(data.get("reason") or f"자동 차단 by {actor}")[:200],
        blocked_by=actor[:80],
    )
    event = SecurityEvent(
        student=str(data.get("student") or actor)[:50],
        src_ip=ip,
        fail_count=fail_count,
        decision="deny",
        severity=str(data.get("severity") or "High")[:10],
        reason=str(data.get("reason") or f"IP 실차단: {ip}")[:200],
        users="",
        source=str(data.get("source") or "ip-guard")[:50],
        generated_at=data.get("generated_at"),
    )
    db.session.add_all((row, event))
    db.session.commit()
    return jsonify(
        {
            "msg": "IP 차단 완료",
            "ip": ip,
            "blocked": True,
            "changed": True,
            "event_id": event.id,
            "blocked_by": actor,
        }
    )


@admin_bp.post("/unblock")
@_admin_or_api_key_required
def unblock_ip():
    """IP 차단을 해제한다."""
    data = request.get_json(silent=True) or {}
    ip = str(data.get("ip") or data.get("src_ip") or "").strip()
    if not ip:
        return jsonify({"msg": "ip는 필수입니다."}), 400
    row = db.session.get(BlockedIP, ip)
    if row:
        db.session.delete(row)
        db.session.commit()
    return jsonify(
        {
            "msg": "차단 해제 완료",
            "ip": ip,
            "blocked": False,
            "unblocked_by": _security_actor(),
        }
    )


@admin_bp.get("/blocked")
@_admin_or_api_key_required
def list_blocked_ips():
    rows = BlockedIP.query.order_by(BlockedIP.blocked_at.desc()).all()
    return jsonify({"count": len(rows), "blocked": [row.to_dict() for row in rows]})


_SEVERITY_RANK = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}


def _build_incident_summary(src_ip, events):
    by_source = {}
    actions = set()
    worst = "Low"
    timeline = []
    for event in events:
        by_source[event.source] = by_source.get(event.source, 0) + 1
        if event.decision:
            actions.add(event.decision)
        if _SEVERITY_RANK.get(event.severity, 1) > _SEVERITY_RANK.get(worst, 1):
            worst = event.severity
        occurred_at = (
            event.created_at.strftime("%Y-%m-%d %H:%M:%S")
            if event.created_at
            else (event.generated_at or "?")
        )
        timeline.append(
            f"- {occurred_at} [{event.severity}/{event.source}] "
            f"{event.reason or ''} (users={event.users or '-'})"
        )

    first = events[-1].created_at if events and events[-1].created_at else None
    last = events[0].created_at if events and events[0].created_at else None
    source_summary = ", ".join(
        f"{source}×{count}" for source, count in sorted(by_source.items())
    )
    action_summary = ", ".join(sorted(actions)) or "없음"
    summary = (
        f"[인시던트 요약] 출발지 {src_ip}\n"
        f"- 관련 이벤트: {len(events)}건 ({source_summary})\n"
        f"- 최초/최종: {first} ~ {last}\n"
        f"- 취해진 조치: {action_summary}\n"
        f"- 최고 심각도: {worst}\n"
        "[타임라인]\n"
        + "\n".join(timeline[:20])
    )
    return summary, worst, action_summary, len(events)


@admin_bp.post("/incident")
@_admin_or_api_key_required
def create_incident():
    """최근 보안 이벤트를 모아 열린 인시던트를 생성하거나 갱신한다."""
    data = request.get_json(silent=True) or {}
    src_ip = str(data.get("src_ip") or data.get("ip") or "").strip()
    if not src_ip:
        return jsonify({"msg": "src_ip는 필수입니다."}), 400
    hours, error = _as_nonnegative_int(data.get("hours"), "hours", default=24)
    if error or hours == 0:
        return jsonify({"msg": error or "hours는 1 이상이어야 합니다."}), 400

    since = datetime.now() - timedelta(hours=hours)
    last_closed = (
        Incident.query.filter_by(src_ip=src_ip, status="closed")
        .filter(Incident.closed_at.isnot(None))
        .order_by(Incident.closed_at.desc()).first()
    )
    if last_closed and last_closed.closed_at > since:
        since = last_closed.closed_at
    events = (
        SecurityEvent.query.filter(
            SecurityEvent.src_ip == src_ip,
            SecurityEvent.created_at >= since,
        )
        .order_by(SecurityEvent.created_at.desc())
        .all()
    )
    summary, worst, actions, event_count = _build_incident_summary(src_ip, events)
    severity = str(data.get("severity") or worst)
    if severity not in _SEVERITY_RANK:
        return jsonify({"msg": "severity 값이 올바르지 않습니다."}), 400
    title = str(
        data.get("title") or f"보안 인시던트: {src_ip} ({event_count}건)"
    )[:200]

    incident = Incident.query.filter_by(src_ip=src_ip, status="open").first()
    created = incident is None
    if created:
        incident = Incident(src_ip=src_ip, status="open", title=title)
        db.session.add(incident)
    incident.title = title
    # 이미 열린 티켓의 심각도와 실제 이벤트의 최고 등급은 낮추지 않는다.
    incident.severity = max(
        (severity, worst, incident.severity or "Low"),
        key=lambda value: _SEVERITY_RANK.get(value, 0),
    )
    incident.summary = summary
    incident.event_count = event_count
    incident.actions = actions[:255]
    incident.student = str(data.get("student") or _security_actor())[:50]
    db.session.commit()
    return (
        jsonify(
            {
                "msg": "인시던트 생성" if created else "인시던트 갱신",
                "created": created,
                "incident": incident.to_dict(),
            }
        ),
        201 if created else 200,
    )


@admin_bp.get("/incidents")
@_admin_or_api_key_required
def list_incidents():
    status = request.args.get("status")
    query = Incident.query
    if status in ("open", "closed"):
        query = query.filter_by(status=status)
    rows = query.order_by(Incident.updated_at.desc()).all()
    return jsonify(
        {"count": len(rows), "incidents": [incident.to_dict() for incident in rows]}
    )


@admin_bp.post("/incident/close")
@_admin_or_api_key_required
def close_incident():
    data = request.get_json(silent=True) or {}
    incident_id, error = _as_nonnegative_int(data.get("id"), "id")
    if error or not incident_id:
        return jsonify({"msg": error or "id는 필수입니다."}), 400
    incident = db.session.get(Incident, incident_id)
    if incident is None:
        return jsonify({"msg": "없는 인시던트"}), 404
    if incident.status != "closed":
        incident.status = "closed"
        incident.closed_at = datetime.now()
        db.session.commit()
    return jsonify({"msg": "인시던트 종료", "incident": incident.to_dict()})


@admin_bp.post("/incidents/close")
@_admin_or_api_key_required
def close_incidents_bulk():
    """선택 또는 학생·심각도 조건의 열린 티켓 전부 종료(다른 페이지 포함)."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"msg": "JSON 객체가 필요합니다."}), 400
    query = Incident.query.filter_by(status="open")
    wanted = _parse_ids(data)
    if data.get("all_open") is True:
        severity = data.get("severity")
        if severity:
            if not isinstance(severity, str) or severity not in _SEVERITY_RANK:
                return jsonify({"msg": "severity 값이 올바르지 않습니다."}), 400
            query = query.filter_by(severity=severity)
        if data.get("student"):
            query = query.filter_by(student=str(data["student"]))
        targets, skipped, not_found = query.order_by(Incident.id).all(), [], []
    elif wanted is not None:
        targets = query.filter(Incident.id.in_(wanted)).order_by(Incident.id).all()
        known = {value for (value,) in db.session.query(Incident.id).filter(Incident.id.in_(wanted))}
        skipped = sorted(known - {incident.id for incident in targets})
        not_found = sorted(wanted - known)
    else:
        return jsonify({"msg": f"ids(양의 정수 목록, 1~{_BULK_MAX}개) 또는 all_open: true가 필요합니다."}), 400
    now = datetime.now()
    for incident in targets:
        incident.status, incident.closed_at = "closed", now
    db.session.commit()
    closed = [incident.id for incident in targets]
    return jsonify(msg=f"인시던트 {len(closed)}건 종료", count=len(closed), closed=closed,
                   skipped=skipped, not_found=not_found, actor=_security_actor())
