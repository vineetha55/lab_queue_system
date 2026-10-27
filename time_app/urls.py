from django.urls import path
from . import views

urlpatterns = [
    path("home/", views.home, name="home"),
    path(
        "review-bill/<int:bill_id>/",
        views.review_bill,
        name="review_bill",
    ),
path(
    "waiting-dashboard/",
    views.waiting_dashboard,
    name="waiting_dashboard",
),
    path("",views.login_view, name="login_view"),
    path("Logout/",views.logout_view, name="logout_view"),
    path("admin_home/", views.admin_home, name="admin_home"),
    path("branch_dashboard/", views.branch_dashboard, name="branch_dashboard"),
    path("branch/", views.branch, name="branch"),
    path("create_branch/", views.create_branch, name="create_branch"),
    path("edit_branch/<int:branch_id>/", views.edit_branch, name="edit_branch"),
    path("delete_branch/<int:branch_id>/", views.delete_branch, name="delete_branch"),
    path(
        "bill-confirmation/<int:bill_id>/",
        views.bill_confirmation,
        name="bill-confirmation"
    ),

    path(
        "send-sms/<int:bill_id>/",
        views.send_waiting_sms,
        name="send-waiting-sms"
    ),

    path(
        "patient-status/<uuid:token>/",
        views.patient_status,
        name="patient-status"
    ),

]