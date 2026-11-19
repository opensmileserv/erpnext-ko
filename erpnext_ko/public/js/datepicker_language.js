const user = frappe.boot && frappe.boot.user;

if (user && !user.language) {
	user.language = frappe.boot.lang;
}
