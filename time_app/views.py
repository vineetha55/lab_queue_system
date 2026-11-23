
from django.contrib.auth import authenticate, login, logout

from .ocr_utils import extract_bill_text
import pytesseract

# pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
def index(request):
    return render(request, "index.html")


from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta


def search_bill(request):

    bill_number = request.GET.get("bill_number", "").strip()

    error = None
    bill = None

    b = tbl_Branch.objects.first()

    if "bill_number" in request.GET:

        if not bill_number:

            error = "Please enter your laboratory bill number."

        else:

            bill = Collection.objects.filter(
                lab_number__iexact=bill_number
            ).first()

            if not bill:

                error = (
                    "No bill found. Please check your bill number "
                    "and try again."
                )

    return render(
        request,
        "bill_search_result.html",
        {
            "error": error,
            "bill": bill,
            "bill_number": bill_number,
            "b": b,
        }
    )

from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import Collection


@require_GET
def check_bill_number(request):
    bill_number = request.GET.get("bill_number", "").strip()

    if not bill_number:
        return JsonResponse({
            "exists": False,
            "message": "Please enter your laboratory bill number."
        })

    bill_exists = Collection.objects.filter(
        lab_number__iexact=bill_number
    ).exists()

    if bill_exists:
        return JsonResponse({
            "exists": True,
            "message": "Bill number verified successfully."
        })

    return JsonResponse({
        "exists": False,
        "message": "The bill number is incorrect. Please check your bill number and try again."
    })



from django.shortcuts import render
from django.contrib import messages


from django.shortcuts import render, redirect
from django.contrib import messages


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Collection, tbl_Branch


def home(request):

    if request.method == "POST":

        image = request.FILES.get("bill_image")

        # ==========================================
        # OPTION 1: OCR IMAGE PROCESSING
        # ==========================================
        if image:

            try:
                extracted_text = extract_bill_text(image)

                image.seek(0)

                details = parse_bill_details(extracted_text)

                branch_id = request.session.get("bch")

                if not branch_id:
                    return render(request, "home.html", {
                        "error": "Branch session expired. Please login again."
                    })

                branch = get_object_or_404(
                    tbl_Branch,
                    id=branch_id
                )

                bill = Collection.objects.create(
                    branch=branch,
                    image=image,
                    ocr_text=extracted_text,
                    **details
                )

                messages.success(
                    request,
                    "Bill image processed successfully. Please review the details."
                )

                return redirect(
                    "review_bill",
                    bill_id=bill.id
                )

            except Exception as exc:

                return render(request, "home.html", {
                    "error": f"Bill processing failed: {exc}"
                })

        # ==========================================
        # OPTION 2: DIRECT MANUAL BILL ENTRY
        # ==========================================
        else:

            patient_name = request.POST.get(
                "patient_name", ""
            ).strip()

            lab_number = request.POST.get(
                "lab_number", ""
            ).strip()

            phone = request.POST.get(
                "phone", ""
            ).strip()

            # Get all selected test purposes
            selected_purposes = request.POST.getlist("purpose")

            purpose = ", ".join(selected_purposes)

            note = request.POST.get(
                "note", ""
            ).strip()

            urgent = request.POST.get(
                "urgent", "no"
            ).strip().lower()

            # ==========================================
            # VALIDATION
            # ==========================================

            if not patient_name:
                return render(request, "home.html", {
                    "error": "Please enter the patient name."
                })

            if not lab_number:
                return render(request, "home.html", {
                    "error": "Please enter the invoice number."
                })

            if not selected_purposes:
                return render(request, "home.html", {
                    "error": "Please select at least one test purpose."
                })

            if urgent not in ["yes", "no"]:
                urgent = "no"

            # ==========================================
            # GET BRANCH
            # ==========================================

            branch_id = request.session.get("bch")

            if not branch_id:
                return render(request, "home.html", {
                    "error": "Branch session expired. Please login again."
                })

            try:

                branch = get_object_or_404(
                    tbl_Branch,
                    id=branch_id
                )

                # ==========================================
                # SAVE MANUAL BILL DETAILS
                # ==========================================

                bill = Collection.objects.create(
                    branch=branch,
                    patient_name=patient_name,
                    lab_number=lab_number,
                    phone=phone,
                    purpose=purpose,
                    urgent=(urgent == "yes"),
                    note=note,
                    image=None,
                    ocr_text=""
                )

                messages.success(
                    request,
                    "Bill created successfully."
                )

                # ==========================================
                # BILL CONFIRMATION
                # ==========================================

                return redirect(
                    "bill-confirmation",
                    bill_id=bill.id
                )

            except Exception as exc:

                return render(request, "home.html", {
                    "error": f"Manual bill creation failed: {exc}"
                })

    # ==========================================
    # GET REQUEST
    # ==========================================

    return render(request, "home.html")




import re
from datetime import datetime
from decimal import Decimal

import re

def parse_bill_details(text):
    details = {
        "lab_number": "",
        "phone": "",
        "patient_name": "",
    }

    # Patient name: AIM NAME Mr. RENI 56Y/M
    match = re.search(
        r"(?:AIM\s+NAME|PATIENT\s+NAME|NAME)\s*:?\s*"
        r"(?:Mr\.?|Mrs\.?|Ms\.?)?\s*"
        r"([A-Za-z][A-Za-z .'-]*?)"
        r"(?=\s+\d{1,3}\s*Y\s*/\s*(?:M|F|MALE|FEMALE)\b|\s*$)",
        text,
        re.IGNORECASE,
    )

    if match:
        details["patient_name"] = match.group(1).strip()

    # Lab number: LAB NO 69187
    match = re.search(
        r"LAB\s*NO\.?\s*:?\s*(\d+)",
        text,
        re.IGNORECASE,
    )

    if match:
        details["lab_number"] = match.group(1)

    # Phone number: Extract ONLY from PHONE NO label
    match = re.search(
        r"PHONE\s*NO\.?\s*:?\s*"
        r"(\+?\d[\d\s()-]{7,}\d)",
        text,
        re.IGNORECASE,
    )

    if match:
        details["phone"] = re.sub(r"\s+", "", match.group(1)).strip()

    return details



from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Collection, tbl_Branch


def review_bill(request, bill_id):

    # Get the bill
    bill = get_object_or_404(
        Collection,
        id=bill_id
    )

    if request.method == "POST":

        # Get logged-in branch
        branch_id = request.session.get("bch")

        if not branch_id:
            messages.error(
                request,
                "Branch session expired. Please log in again."
            )
            return redirect("Login")

        # Get branch
        branch = get_object_or_404(
            tbl_Branch,
            id=branch_id
        )

        # Ensure the bill belongs to this branch
        if bill.branch_id and bill.branch_id != branch.id:
            messages.error(
                request,
                "You are not authorized to update this bill."
            )
            return redirect("home")

        # Update patient details
        bill.branch = branch

        bill.patient_name = request.POST.get(
            "patient_name", ""
        ).strip()

        bill.lab_number = request.POST.get(
            "lab_number", ""
        ).strip()

        bill.phone = request.POST.get(
            "phone", ""
        ).strip()

        # Handle multiple test purposes if checkboxes are used
        selected_purposes = request.POST.getlist("purpose")

        if selected_purposes:
            bill.purpose = ", ".join(selected_purposes)
        else:
            # Also support a normal single-value input
            bill.purpose = request.POST.get(
                "purpose", ""
            ).strip()

        # Update note
        bill.note = request.POST.get(
            "note", ""
        ).strip()

        # Update urgent status
        bill.urgent = (
            request.POST.get("urgent") == "yes"
        )

        # Update uploaded image only if a new image is provided
        new_image = request.FILES.get("bill_image")

        if new_image:
            bill.image = new_image

        # Validate required fields
        if not bill.patient_name:
            messages.error(
                request,
                "Patient name is required."
            )
            return redirect(
                "review_bill",
                bill_id=bill.id
            )

        if not bill.lab_number:
            messages.error(
                request,
                "Lab number is required."
            )
            return redirect(
                "review_bill",
                bill_id=bill.id
            )

        if not bill.purpose:
            messages.error(
                request,
                "Please select at least one test purpose."
            )
            return redirect(
                "review_bill",
                bill_id=bill.id
            )

        bill.save()

        messages.success(
            request,
            "Bill details updated successfully."
        )

        return redirect(
            "bill-confirmation",
            bill_id=bill.id
        )

    return render(
        request,
        "review_bill.html",
        {
            "bill": bill,
        }
    )


def login_view(request):

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        print("LOGIN ATTEMPT:", username)

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            print("ADMIN LOGIN SUCCESS")

            login(request, user)

            return redirect("admin_home")

        branch = tbl_Branch.objects.filter(
            username=username,
            password=password
        ).first()

        if branch:
            print("BRANCH LOGIN SUCCESS:", branch.id)

            request.session["bch"] = branch.id

            return redirect("home")

        print("LOGIN FAILED")

        messages.error(request, "Invalid username or password.")

    return render(request, "login.html")

from django.shortcuts import redirect
from django.contrib.auth import logout

def logout_view(request):

    if request.session.get("bch"):
        del request.session["bch"]

    else:
        logout(request)

    return redirect("login_view")


    
import json
from datetime import date, datetime, timedelta
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth



import json

from datetime import date, timedelta

from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import TruncDate, TruncMonth

from .models import (
    tbl_Branch,
    Collection,
    CollectionSampleReceipt
)


def admin_home(request):

    # ==========================================
    # DATE SETTINGS
    # ==========================================

    today = timezone.localdate()

    filter_options = [
        ("today", "Today"),
        ("yesterday", "Yesterday"),
        ("weekly", "Last 7 Days"),
        ("monthly", "This Month"),
        ("yearly", "This Year"),
        ("custom", "Custom"),
    ]

    selected_filter = request.GET.get("filter", "today")

    valid_filters = [
        "today",
        "yesterday",
        "weekly",
        "monthly",
        "yearly",
        "custom",
    ]

    if selected_filter not in valid_filters:
        selected_filter = "today"

    start_date = today
    end_date = today

    # ==========================================
    # DATE FILTER
    # ==========================================

    if selected_filter == "today":

        start_date = today
        end_date = today

    elif selected_filter == "yesterday":

        start_date = today - timedelta(days=1)
        end_date = start_date

    elif selected_filter == "weekly":

        start_date = today - timedelta(days=6)
        end_date = today

    elif selected_filter == "monthly":

        start_date = today.replace(day=1)
        end_date = today

    elif selected_filter == "yearly":

        start_date = today.replace(month=1, day=1)
        end_date = today

    elif selected_filter == "custom":

        try:

            start_date = date.fromisoformat(
                request.GET.get("start_date", "")
            )

            end_date = date.fromisoformat(
                request.GET.get("end_date", "")
            )

            if start_date > end_date:
                raise ValueError

            if end_date > today:
                raise ValueError

        except (ValueError, TypeError):

            selected_filter = "today"

            start_date = today
            end_date = today

    # ==========================================
    # BASE QUERYSETS
    # ==========================================

    all_bills = Collection.objects.all()

    all_receipts = CollectionSampleReceipt.objects.select_related(
        "collection",
        "collection__branch"
    ).all()

    # ==========================================
    # FILTERED DATA
    # ==========================================

    bills = all_bills.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    )

    receipts = all_receipts.filter(
        collection__created_at__date__gte=start_date,
        collection__created_at__date__lte=end_date
    )

    # ==========================================
    # BRANCH COUNT
    # ==========================================

    total_branches = tbl_Branch.objects.count()

    # ==========================================
    # PATIENT / BILL STATISTICS
    # ==========================================

    total_bills = bills.count()

    total_patients = (
        bills.exclude(
            Q(phone__isnull=True) | Q(phone="")
        )
        .values("phone")
        .distinct()
        .count()
    )

    urgent_bills = bills.filter(
        urgent=True
    ).count()

    normal_bills = bills.filter(
        urgent=False
    ).count()

    # ==========================================
    # SAMPLE RECEIPT STATISTICS
    # ==========================================

    total_collections = receipts.count()

    completed_collections = receipts.filter(
        is_received=True
    ).count()

    pending_collections = receipts.filter(
        is_received=False
    ).count()

    # ==========================================
    # TODAY STATISTICS
    # ==========================================

    today_bills_qs = all_bills.filter(
        created_at__date=today
    )

    today_bills = today_bills_qs.count()

    today_urgent_bills = today_bills_qs.filter(
        urgent=True
    ).count()

    today_normal_bills = today_bills_qs.filter(
        urgent=False
    ).count()

    today_patients = (
        today_bills_qs.exclude(
            Q(phone__isnull=True) | Q(phone="")
        )
        .values("phone")
        .distinct()
        .count()
    )

    today_receipts_qs = all_receipts.filter(
        collection__created_at__date=today
    )

    today_collections = today_receipts_qs.count()

    today_completed_collections = today_receipts_qs.filter(
        is_received=True
    ).count()

    today_pending_collections = today_receipts_qs.filter(
        is_received=False
    ).count()

    # ==========================================
    # COMPLETION PERCENTAGE
    # ==========================================

    if total_collections:

        completion_percentage = round(
            completed_collections / total_collections * 100,
            1
        )

        pending_percentage = round(
            pending_collections / total_collections * 100,
            1
        )

    else:

        completion_percentage = 0
        pending_percentage = 0

    # ==========================================
    # CHART TYPE
    # ==========================================

    date_difference = (end_date - start_date).days

    monthly_chart = (
        selected_filter == "yearly"
        or date_difference > 90
    )

    # ==========================================
    # PATIENT CHART DATA
    # ==========================================

    if monthly_chart:

        patient_data = (
            bills.annotate(
                period=TruncMonth("created_at")
            )
            .values("period")
            .annotate(
                total=Count("id")
            )
            .order_by("period")
        )

    else:

        patient_data = (
            bills.annotate(
                period=TruncDate("created_at")
            )
            .values("period")
            .annotate(
                total=Count("id")
            )
            .order_by("period")
        )

    patient_chart = {}

    for item in patient_data:

        period = item["period"]

        if period:

            if monthly_chart:

                key = period.date().replace(
                    day=1
                ).isoformat()

            else:

                key = period.isoformat()

            patient_chart[key] = item["total"]

    # ==========================================
    # SAMPLE RECEIPT CHART DATA
    # ==========================================

    if monthly_chart:

        collection_data = (
            receipts.annotate(
                period=TruncMonth(
                    "collection__created_at"
                )
            )
            .values("period")
            .annotate(

                total=Count("id"),

                completed=Count(
                    "id",
                    filter=Q(is_received=True)
                ),

                pending=Count(
                    "id",
                    filter=Q(is_received=False)
                )

            )
            .order_by("period")
        )

    else:

        collection_data = (
            receipts.annotate(
                period=TruncDate(
                    "collection__created_at"
                )
            )
            .values("period")
            .annotate(

                total=Count("id"),

                completed=Count(
                    "id",
                    filter=Q(is_received=True)
                ),

                pending=Count(
                    "id",
                    filter=Q(is_received=False)
                )

            )
            .order_by("period")
        )

    collection_chart = {}

    for item in collection_data:

        period = item["period"]

        if period:

            if monthly_chart:

                key = period.date().replace(
                    day=1
                ).isoformat()

            else:

                key = period.isoformat()

            collection_chart[key] = item

    # ==========================================
    # GENERATE CHART LABELS
    # ==========================================

    chart_labels = []

    patient_chart_values = []

    collection_chart_values = []

    completed_chart_values = []

    pending_chart_values = []

    if monthly_chart:

        current_date = start_date.replace(day=1)

        last_month = end_date.replace(day=1)

        while current_date <= last_month:

            key = current_date.isoformat()

            chart_labels.append(
                current_date.strftime("%b %Y")
            )

            patient_chart_values.append(
                patient_chart.get(key, 0)
            )

            item = collection_chart.get(key, {})

            collection_chart_values.append(
                item.get("total", 0)
            )

            completed_chart_values.append(
                item.get("completed", 0)
            )

            pending_chart_values.append(
                item.get("pending", 0)
            )

            if current_date.month == 12:

                current_date = date(
                    current_date.year + 1,
                    1,
                    1
                )

            else:

                current_date = date(
                    current_date.year,
                    current_date.month + 1,
                    1
                )

    else:

        current_date = start_date

        while current_date <= end_date:

            key = current_date.isoformat()

            chart_labels.append(
                current_date.strftime("%d %b")
            )

            patient_chart_values.append(
                patient_chart.get(key, 0)
            )

            item = collection_chart.get(key, {})

            collection_chart_values.append(
                item.get("total", 0)
            )

            completed_chart_values.append(
                item.get("completed", 0)
            )

            pending_chart_values.append(
                item.get("pending", 0)
            )

            current_date += timedelta(days=1)

    # ==========================================
    # BRANCH-WISE BILL STATISTICS
    # ==========================================

    branch_data = (
        bills.values("branch__name")
        .annotate(
            total=Count("id")
        )
        .order_by("-total")
    )

    branch_labels = [
        item["branch__name"] or "Unknown Branch"
        for item in branch_data
    ]

    branch_values = [
        item["total"]
        for item in branch_data
    ]

    # ==========================================
    # URGENCY STATISTICS
    # ==========================================

    urgency_labels = [
        "Urgent",
        "Normal"
    ]

    urgency_values = [
        urgent_bills,
        normal_bills
    ]

    # ==========================================
    # CHART JSON DATA
    # ==========================================

    chart_data = {

        "labels": chart_labels,

        "patients": patient_chart_values,

        "collections": collection_chart_values,

        "completed": completed_chart_values,

        "pending": pending_chart_values,

        "branches": {

            "labels": branch_labels,

            "values": branch_values

        },

        "urgency": {

            "labels": urgency_labels,

            "values": urgency_values

        }

    }

    # ==========================================
    # TEMPLATE CONTEXT
    # ==========================================

    context = {

        # Date filters

        "filter_options": filter_options,

        "selected_filter": selected_filter,

        "start_date": start_date.isoformat(),

        "end_date": end_date.isoformat(),

        "monthly_chart": monthly_chart,

        # Branch

        "total_branches": total_branches,

        # Patient / Bill

        "total_bills": total_bills,

        "total_patients": total_patients,

        "urgent_bills": urgent_bills,

        "normal_bills": normal_bills,

        # Sample receipts

        "total_collections": total_collections,

        "completed_collections": completed_collections,

        "pending_collections": pending_collections,

        # Today's statistics

        "today_bills": today_bills,

        "today_patients": today_patients,

        "today_urgent_bills": today_urgent_bills,

        "today_normal_bills": today_normal_bills,

        "today_collections": today_collections,

        "today_completed_collections": today_completed_collections,

        "today_pending_collections": today_pending_collections,

        # Percentages

        "completion_percentage": completion_percentage,

        "pending_percentage": pending_percentage,

        # Charts

        "chart_data": json.dumps(chart_data),

    }

    return render(
        request,
        "admin_home.html",
        context
    )


def branch_dashboard(request):
    return render(request, "branch_dashboard.html")

def branch(request):
    data=tbl_Branch.objects.all()
    context={
        "data": data,
    }
    return render(request, "branch.html",context)


from django.shortcuts import render, get_object_or_404
from django.db.models import Count
from django.utils import timezone


# =====================================================
# BRANCH LIST
# =====================================================
def tests(request):

    data = tbl_Branch.objects.all().order_by('-created_at')

    context = {
        "data": data,
    }

    return render(request, "tests.html", context)


def branch_report(request, branch_id):

    branch = get_object_or_404(
        tbl_Branch,
        id=branch_id
    )

    collections = Collection.objects.filter(
        branch=branch
    ).order_by('-created_at')

    context = {
        "branch": branch,
        "collections": collections,
    }

    return render(
        request,
        "branch_report.html",
        context
    )


# =====================================================
# INDIVIDUAL BRANCH REPORT
# =====================================================

from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Avg



from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Avg


from datetime import datetime, timedelta

from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.db.models import Count, Q

from .models import (
    tbl_Branch,
    Collection,
    CollectionSampleReceipt
)


def branch_report(request, branch_id):

    # ==========================================
    # GET BRANCH
    # ==========================================

    branch = get_object_or_404(
        tbl_Branch,
        id=branch_id
    )

    today = timezone.localdate()

    # ==========================================
    # DATE FILTER
    # ==========================================

    selected_filter = request.GET.get(
        'filter',
        'today'
    )

    allowed_filters = [
        'today',
        'yesterday',
        'weekly',
        'monthly',
        'yearly',
        'custom'
    ]

    if selected_filter not in allowed_filters:
        selected_filter = 'today'

    from_date = request.GET.get('from_date', '')
    to_date = request.GET.get('to_date', '')

    start_date = today
    end_date = today

    if selected_filter == 'today':

        start_date = today
        end_date = today

    elif selected_filter == 'yesterday':

        start_date = today - timedelta(days=1)
        end_date = start_date

    elif selected_filter == 'weekly':

        start_date = today - timedelta(
            days=today.weekday()
        )

        end_date = start_date + timedelta(days=6)

    elif selected_filter == 'monthly':

        start_date = today.replace(day=1)

        if today.month == 12:
            next_month = today.replace(
                year=today.year + 1,
                month=1,
                day=1
            )
        else:
            next_month = today.replace(
                month=today.month + 1,
                day=1
            )

        end_date = next_month - timedelta(days=1)

    elif selected_filter == 'yearly':

        start_date = today.replace(
            month=1,
            day=1
        )

        end_date = today.replace(
            month=12,
            day=31
        )

    elif selected_filter == 'custom':

        try:

            if not from_date or not to_date:
                raise ValueError

            start_date = datetime.strptime(
                from_date,
                '%Y-%m-%d'
            ).date()

            end_date = datetime.strptime(
                to_date,
                '%Y-%m-%d'
            ).date()

            if start_date > end_date:
                raise ValueError

        except (ValueError, TypeError):

            selected_filter = 'today'

            start_date = today
            end_date = today

            from_date = ''
            to_date = ''

    # ==========================================
    # FILTER PATIENT / BILL RECORDS
    # ==========================================

    bills = Collection.objects.filter(
        branch=branch,
        created_at__date__range=(
            start_date,
            end_date
        )
    ).prefetch_related(
        'sample_receipts'
    ).order_by('-created_at')

    # ==========================================
    # FILTER SAMPLE RECEIPTS
    # ==========================================

    receipts = CollectionSampleReceipt.objects.filter(
        collection__branch=branch,
        collection__created_at__date__range=(
            start_date,
            end_date
        )
    ).select_related(
        'collection'
    ).order_by(
        '-collection__created_at',
        'id'
    )

    # ==========================================
    # SUMMARY COUNTS
    # ==========================================

    total_patients = bills.count()

    total_tests = receipts.count()

    received_samples = receipts.filter(
        is_received=True
    ).count()

    pending_samples = receipts.filter(
        is_received=False
    ).count()

    urgent_patients = bills.filter(
        urgent=True
    ).count()

    normal_patients = bills.filter(
        urgent=False
    ).count()

    # ==========================================
    # UNIQUE PATIENT COUNT
    # ==========================================

    unique_patients = bills.exclude(
        phone=''
    ).values(
        'phone'
    ).distinct().count()

    # ==========================================
    # RECEIPT PERCENTAGES
    # ==========================================

    completion_percentage = (
        round((received_samples / total_tests) * 100, 2)
        if total_tests > 0
        else 0
    )

    pending_percentage = (
        round((pending_samples / total_tests) * 100, 2)
        if total_tests > 0
        else 0
    )

    # ==========================================
    # URGENT / NORMAL SAMPLE COUNTS
    # ==========================================

    urgent_samples = receipts.filter(
        collection__urgent=True
    ).count()

    normal_samples = receipts.filter(
        collection__urgent=False
    ).count()

    # ==========================================
    # BRANCH SUMMARY
    # ==========================================

    total_received_bills = bills.filter(
        sample_receipts__is_received=True
    ).distinct().count()

    total_pending_bills = bills.filter(
        sample_receipts__is_received=False
    ).distinct().count()

    # ==========================================
    # CONTEXT
    # ==========================================

    context = {

        'branch': branch,

        'bills': bills,
        'collections': receipts,
        'receipts': receipts,

        'selected_filter': selected_filter,

        'start_date': start_date,
        'end_date': end_date,

        'from_date': from_date,
        'to_date': to_date,

        # Patient / Bill Summary
        'total_patients': total_patients,
        'unique_patients': unique_patients,

        'urgent_patients': urgent_patients,
        'normal_patients': normal_patients,

        # Sample Summary
        'total_tests': total_tests,
        'received_samples': received_samples,
        'pending_samples': pending_samples,

        'urgent_samples': urgent_samples,
        'normal_samples': normal_samples,

        'completion_percentage': completion_percentage,
        'pending_percentage': pending_percentage,

        # Bill Receipt Summary
        'total_received_bills': total_received_bills,
        'total_pending_bills': total_pending_bills,

        # Report Date
        'report_generated_at': timezone.localtime(),

    }

    return render(
        request,
        'branch_report.html',
        context
    )




def create_branch(request):
    if request.method == "POST":
        obj=tbl_Branch()
        obj.name=request.POST.get("name", "")
        obj.email=request.POST.get("email", "")
        obj.phone=request.POST.get("phone", "")
        obj.address=request.POST.get("address", "")
        obj.username=request.POST.get("username", "")
        obj.password=request.POST.get("password", "")
        obj.save()
        return redirect("branch")
    return render(request, "create_branch.html")


def edit_branch(request, branch_id):
    branch = get_object_or_404(tbl_Branch, pk=branch_id)
    if request.method == "POST":
        branch.name=request.POST.get("name", "")
        branch.email=request.POST.get("email", "")
        branch.phone=request.POST.get("phone", "")
        branch.address=request.POST.get("address", "")
        branch.username = request.POST.get("username", "")
        branch.password = request.POST.get("password", "")
        branch.save()
        return redirect("branch")
    return render(request, "edit_branch.html", {"branch": branch})

def delete_branch(request, branch_id):
    branch = get_object_or_404(tbl_Branch, pk=branch_id)
    branch.delete()
    return redirect("branch")


import base64
import os
from io import BytesIO

import qrcode
import requests

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

import base64
from io import BytesIO

import qrcode

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from .models import Collection, tbl_Branch



def bill_confirmation(request, bill_id):

    # ==========================================
    # GET LOGGED-IN BRANCH
    # ==========================================

    branch_id = request.session.get("bch")

    if not branch_id:
        return redirect("Login")

    branch = get_object_or_404(
        tbl_Branch,
        id=branch_id
    )

    # ==========================================
    # GET BILL BELONGING TO THIS BRANCH
    # ==========================================

    bill = get_object_or_404(
        Collection,
        id=bill_id,
        branch=branch
    )

    # ==========================================
    # GENERATE PATIENT STATUS URL
    # ==========================================

    status_url = request.build_absolute_uri(
        reverse(
            "patient-status",
            kwargs={
                "bill_id": bill.id
            }
        )
    )

    # ==========================================
    # GENERATE QR CODE
    # ==========================================

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3
    )

    qr.add_data(status_url)
    qr.make(fit=True)

    qr_image = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    buffer = BytesIO()

    qr_image.save(
        buffer,
        format="PNG"
    )

    qr_code = base64.b64encode(
        buffer.getvalue()
    ).decode("utf-8")

    # ==========================================
    # FORMAT TESTS (COMMA SEPARATED VALUES)
    # ==========================================

    purpose_display = (
        bill.purpose.replace(",", "\n")
        if bill.purpose
        else "N/A"
    )

    # ==========================================
    # RENDER CONFIRMATION PAGE
    # ==========================================

    return render(
        request,
        "bill_confirmation.html",
        {
            "bill": bill,
            "qr_code": qr_code,
            "status_url": status_url,
            "b": branch,
            "purpose_display": purpose_display,
        }
    )



from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from .models import Collection, CollectionSampleReceipt

def collection_detail(request, collection_id):

    # ==========================================
    # GET LOGGED-IN BRANCH
    # ==========================================

    branch_id = request.session.get("bch")

    if not branch_id:
        return redirect("Login")

    # ==========================================
    # GET COLLECTION
    # ==========================================

    collection = get_object_or_404(
        Collection,
        id=collection_id,
        branch_id=branch_id
    )

    # ==========================================
    # GET COLLECTION PURPOSES
    # ==========================================

    purposes = []

    if collection.purpose:

        purposes = [
            item.strip()
            for item in collection.purpose.replace("\n", ",").split(",")
            if item.strip()
        ]

    # ==========================================
    # CREATE INDIVIDUAL SAMPLE RECORDS
    # ==========================================

    for purpose in purposes:

        CollectionSampleReceipt.objects.get_or_create(
            collection=collection,
            sample_name=purpose
        )

    # ==========================================
    # SAVE CHECKBOX STATUS
    # ==========================================

    if request.method == "POST":

        selected_samples = request.POST.getlist("received_samples")

        current_datetime = timezone.localtime(timezone.now())

        sample_records = CollectionSampleReceipt.objects.filter(
            collection=collection
        )

        for sample in sample_records:

            if sample.sample_name in selected_samples:

                if not sample.is_received:

                    sample.is_received = True

                    sample.received_date = current_datetime.date()

                    sample.received_time = current_datetime.time().replace(
                        microsecond=0
                    )

                    sample.save()

            else:

                sample.is_received = False
                sample.received_date = None
                sample.received_time = None

                sample.save()

        # Redirect to collection list
        return redirect("collection_list")

    # ==========================================
    # GET SAMPLE RECEIPTS
    # ==========================================

    received_samples = CollectionSampleReceipt.objects.filter(
        collection=collection
    )

    return render(request, "collection_detail.html", {
        "collection": collection,
        "purposes": purposes,
        "received_samples": received_samples
    })

# ==========================================
# COLLECTION LIST
# ==========================================

from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.dateparse import parse_date
from datetime import timedelta


def collection_list(request):

    # ==========================================
    # CHECK BRANCH LOGIN
    # ==========================================

    branch = request.session.get("bch")

    if not branch:
        return redirect("Login")

    # ==========================================
    # CURRENT DATE
    # ==========================================

    today = timezone.localdate()

    # ==========================================
    # GET FILTER VALUES
    # DEFAULT FILTER = TODAY
    # ==========================================

    filter_type = request.GET.get("filter", "today")

    start_date = request.GET.get("start_date", "")
    end_date = request.GET.get("end_date", "")

    # ==========================================
    # BASE COLLECTION QUERYSET
    # ==========================================

    collections = Collection.objects.filter(
        branch=branch
    ).prefetch_related(
        "sample_receipts"
    )

    # ==========================================
    # DATE FILTER
    # ==========================================

    if filter_type == "today":

        collections = collections.filter(
            created_at__date=today
        )

    elif filter_type == "yesterday":

        yesterday = today - timedelta(days=1)

        collections = collections.filter(
            created_at__date=yesterday
        )

    elif filter_type == "weekly":

        week_start = today - timedelta(
            days=today.weekday()
        )

        collections = collections.filter(
            created_at__date__gte=week_start,
            created_at__date__lte=today
        )

    elif filter_type == "monthly":

        month_start = today.replace(day=1)

        collections = collections.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=today
        )

    elif filter_type == "yearly":

        year_start = today.replace(
            month=1,
            day=1
        )

        collections = collections.filter(
            created_at__date__gte=year_start,
            created_at__date__lte=today
        )

    elif filter_type == "custom":

        parsed_start = (
            parse_date(start_date)
            if start_date else None
        )

        parsed_end = (
            parse_date(end_date)
            if end_date else None
        )

        if parsed_start and parsed_end:

            if parsed_start <= parsed_end:

                collections = collections.filter(
                    created_at__date__gte=parsed_start,
                    created_at__date__lte=parsed_end
                )

        elif parsed_start:

            collections = collections.filter(
                created_at__date__gte=parsed_start
            )

        elif parsed_end:

            collections = collections.filter(
                created_at__date__lte=parsed_end
            )

    elif filter_type == "all":

        pass

    else:

        # Invalid filter defaults to today

        filter_type = "today"

        collections = collections.filter(
            created_at__date=today
        )

    # ==========================================
    # ORDER COLLECTIONS
    # ==========================================

    collections = collections.order_by(
        "-created_at"
    )

    # ==========================================
    # PURPOSE LIST
    # ==========================================

    for item in collections:

        item.purpose_list = [
            purpose.strip()
            for purpose in (item.purpose or "").split(",")
            if purpose.strip()
        ]

        # Count received samples

        item.received_samples_count = (
            item.sample_receipts.filter(
                is_received=True
            ).count()
        )

    # ==========================================
    # SUMMARY COUNTS
    # ==========================================

    total_count = collections.count()

    urgent_count = collections.filter(
        urgent=True
    ).count()

    normal_count = collections.filter(
        urgent=False
    ).count()

    # ==========================================
    # RENDER TEMPLATE
    # ==========================================

    return render(
        request,
        "collection_list.html",
        {
            "branch": branch,
            "collections": collections,

            "total_count": total_count,
            "urgent_count": urgent_count,
            "normal_count": normal_count,

            "filter_type": filter_type,
            "start_date": start_date,
            "end_date": end_date,

            "today": today,
        }
    )

# ==========================================
# COLLECTION DETAILS
# ==========================================
# ==========================================
# EDIT COLLECTION
# ==========================================

def collection_edit(request, collection_id):

    branch = request.session.get("bch")

    if not branch:
        return redirect("Login")

    collection = get_object_or_404(
        Collection,
        id=collection_id,
        branch=branch
    )

    if request.method == "POST":

        collection.patient_name = request.POST.get(
            "patient_name", ""
        ).strip()

        collection.lab_number = request.POST.get(
            "lab_number", ""
        ).strip()

        collection.phone = request.POST.get(
            "phone", ""
        ).strip()

        collection.purpose = request.POST.get(
            "purpose", ""
        ).strip()

        collection.urgent = request.POST.get("urgent") == "on"

        collection.note = request.POST.get(
            "note", ""
        ).strip()

        new_image = request.FILES.get("image")

        if new_image:
            collection.image = new_image

        if not collection.patient_name or not collection.lab_number or not collection.purpose:
            messages.error(request, "Please fill all required fields.")
            return redirect("collection_edit", collection_id=collection.id)

        collection.save()

        messages.success(request, "Collection updated successfully.")

        return redirect("collection_list")

    return render(request, "collection_edit.html", {
        "branch": branch,
        "collection": collection
    })


# ==========================================
# DELETE COLLECTION
# ==========================================

def collection_delete(request, collection_id):

    branch = request.session.get("bch")

    if not branch:
        return redirect("Login")

    collection = get_object_or_404(
        Collection,
        id=collection_id,
        branch=branch
    )

    if request.method == "POST":

        # Delete associated image file
        if collection.image:
            collection.image.delete(save=False)

        collection.delete()

        messages.success(request, "Collection deleted successfully.")

        return redirect("collection_list")

    return render(request, "collection_delete.html", {
        "collection": collection
    })



    
def patient_status(request, bill_id):

    bill = get_object_or_404(
        Collection,
        id=bill_id
    )

    return render(
        request,
        "patient_status.html",
        {
            "bill": bill
        }
    )