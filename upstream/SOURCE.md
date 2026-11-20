# 원문 템플릿 출처

[tools/update-upstream](../tools/update-upstream) 이 frappe·erpnext 의 `version-16` 브랜치에서 가져온다.

| 파일 | 저장소 | 버전 | 커밋 |
|---|---|---|---|
| `frappe.pot` | frappe/frappe | 16.60.2 | 2df0425 |
| `erpnext.pot` | frappe/erpnext | 16.60.0 | 886ab6a |

`desk.pot` 은 같은 커밋의 데스크 문서(`workspace_sidebar`·`desktop_icon`·`dashboard_chart`·`number_card`)에서 `./kotr extract-desk` 로 뽑는다. 원문에서 사라진 번역은 ko.po 끝에 `#~` 로 보관되고, 같은 문구가 돌아오면 되살아난다.
