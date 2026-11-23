from django.urls import path
from . import views

urlpatterns = [
    path("",views.index,name="index"),
    path("home/", views.home, name="home"),
    path(
        "review-bill/<int:bill_id>/",
        views.review_bill,
        name="review_bill",
    ),

    path("login_view/",views.login_view, name="login_view"),
    path("logout_view/",views.logout_view, name="logout_view"),
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
        "check-bill-number/",
        views.check_bill_number,
        name="check_bill_number"
    ),
    path(
    'bill-confirmation/<int:bill_id>/',
    views.bill_confirmation,
    name='bill-confirmation'
),
    path(
        'tests',
        views.tests,
        name='tests'
    ),
    path(
        'branch_report/<int:branch_id>/',
        views.branch_report,
        name='branch_report'
    ),
path(
    "patient-status/<int:bill_id>/",
    views.patient_status,
    name="patient-status"
),
    path(
        "collections/",
        views.collection_list,
        name="collection_list"
    ),

    path(
        "collection/details/<int:collection_id>/",
        views.collection_detail,
        name="collection_detail"
    ),

    path(
        "collection/edit/<int:collection_id>/",
        views.collection_edit,
        name="collection_edit"
    ),
path(
    'collection/details/<int:collection_id>/',
    views.collection_detail,
    name='collection_detail'
),
    path(
        "collection/delete/<int:collection_id>/",
        views.collection_delete,
        name="collection_delete"
    ),

]