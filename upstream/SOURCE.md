# 원문 템플릿 출처

| 파일 | 앱 | 버전 | 가져온 곳 |
|---|---|---|---|
| `frappe.pot` | frappe | 16.60.2 | `frappe/erpnext:v16.60.0` 이미지의 `apps/frappe/frappe/locale/main.pot` |
| `erpnext.pot` | erpnext | 16.60.0 | 같은 이미지의 `apps/erpnext/erpnext/locale/main.pot` |

새 버전으로 올릴 때는 두 파일을 바꾸고 `./kotr sync` 를 실행한다. 원문에서 사라진 번역은 ko.po 끝에 `#~` 로 보관되고, 같은 문구가 돌아오면 되살아난다.
