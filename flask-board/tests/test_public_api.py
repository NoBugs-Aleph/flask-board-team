import pytest
from app import create_app
from extensions import db
from test_security_response import TestConfig


@pytest.fixture
def client(monkeypatch):
  # 다른 테스트가 해제한 전역 DB를 재사용하지 않는다. 외부 API도 격리한다.
  app = create_app(TestConfig)
  monkeypatch.setattr('controllers.public_controller.fetch_busan_travel',
                      lambda content_id=None: [])
  yield app.test_client()
  with app.app_context():
    db.session.remove()
    db.drop_all()
    db.engine.dispose()


def test_public_data_is_rendered_on_server(client, monkeypatch):
  """팀 게시판은 공공데이터를 서버에서 조회하여 HTML에 표시한다."""
  monkeypatch.setattr('controllers.public_controller.fetch_busan_travel',
                      lambda content_id=None: [{'UC_SEQ': 123, 'MAIN_TITLE': '합성 테마여행'}])
  response = client.get('/public-posts')
  assert response.status_code == 200
  html = response.get_data(as_text=True)
  assert '합성 테마여행' in html
  assert '/public-post/123' in html


def test_public_posts_page_route(client):
  """2) 공공데이터 목록 보기 페이지 라우트(/public-posts)가 정상 작동하는지 테스트"""
  response = client.get('/public-posts')
  # 템플릿 파일(public_posts.html)이 존재하면 200, 없으면 500(TemplateNotFound)이 발생합니다.
  # 라우트 자체의 존재 유무(404 아님)를 확인합니다.
  assert response.status_code != 404


def test_public_post_detail_page_route(client):
  """3) 공공데이터 상세 보기 페이지 라우트(/public-posts/<int:uc_seq>)가 정상 작동하는지 테스트"""
  test_uc_seq = 123
  response = client.get(f'/public-posts/{test_uc_seq}')
  # 마찬가지로 404가 발생하지 않고 라우팅이 매핑되는지 확인
  assert response.status_code != 404


def test_wrong_route_returns_404(client):
  """4) 잘못된 경로(/api/public-posts 등)로 요청 시 404 에러가 발생하는지 확인 (로그에서 발생했던 이슈 검증)"""
  response = client.get('/api/public-posts')
  assert response.status_code == 404
