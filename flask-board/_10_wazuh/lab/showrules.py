import re, sys
src = open('/var/ossec/ruleset/rules/0245-web_rules.xml', encoding='utf-8').read()
for rid in sys.argv[1:]:
    m = re.search(r'<rule id="%s".*?</rule>' % rid, src, re.S)
    print(m.group(0) if m else 'no ' + rid, '\n')
