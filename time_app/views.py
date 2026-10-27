from lib2to3.fixes.fix_input import context

from django.contrib.auth import authenticate, login, logout

from .models import LabBill, tbl_Branch
from .ocr_utils import extract_bill_text

from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

import os
import pytesseract

pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


def home(request):
    if request.method == "POST":
        image = request.FILES.get("bill_image")

        if not image:
            return render(request, "home.html", {
                "error": "Please upload a bill image."
            })

        try:
            extracted_text = extract_bill_text(image)
            image.seek(0)

            details = parse_bill_details(extracted_text)

            bill = LabBill.objects.create(
                image=image,
                ocr_text=extracted_text,
                **details,
            )

            return render(request, "review_bill.html", {
                "bill": bill,
            })

        except Exception as exc:
            return render(request, "home.html", {
                "error": f"Bill processing failed: {exc}"
            })

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

    # Invoice number: LAB NO 69187
    # Lab number
    match = re.search(
        r"LAB\s*NO\.?\s*:?\s*(\d+)",
        text,
        re.IGNORECASE,
    )
    if match:
        details["lab_number"] = match.group(1)

    # Phone number: supports PHONE, MOBILE, CUSTOMER PHONE,
    # and DOCTOR PHONE labels
    match = re.search(
        r"(?:CUSTOMER\s*)?(?:PHONE|MOBILE|CONTACT)"
        r"(?:\s*(?:NO|NUMBER))?\.?\s*:?\s*"
        r"(\+?\d[\d\s()-]{7,}\d)",
        text,
        re.IGNORECASE,
    )

    if match:
        details["phone"] = re.sub(r"\s+", "", match.group(1)).strip()

    return details



def review_bill(request, bill_id):
    bill = get_object_or_404(LabBill, id=bill_id)

    if request.method == "POST":
        b=tbl_Branch.objects.get(id=request.session["bch"])
        bill.branch_id=b.id
        bill.patient_name = request.POST.get("patient_name", "").strip()
        bill.lab_number = request.POST.get("lab_number", "").strip()
        bill.phone = request.POST.get("phone", "").strip()

        # Entered manually by staff
        bill.purpose = request.POST.get("purpose", "").strip()

        waiting_time = request.POST.get("waiting_time", "").strip()
        bill.waiting_time = int(waiting_time) if waiting_time else None

        bill.urgent = request.POST.get("urgent") == 'yes'

        bill.save()

        messages.success(request, "Bill details saved successfully.")
        return redirect("bill-confirmation", bill_id=bill.id)

    return render(request, "review_bill.html", {"bill": bill})


def waiting_dashboard(request):
    b = tbl_Branch.objects.get(id=request.session["bch"])
    bills = LabBill.objects.filter(
        branch=request.session['bch']
    ).order_by("-id")

    return render(
        request,
        "waiting_dashboard.html",
        {"bills": bills,
         'b':b},
    )


def login_view(request):
    if request.method=="POST":
        username=request.POST.get("username", "")
        password = request.POST.get("password", "")
        user=authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("admin_home")
        elif tbl_Branch.objects.filter(username=username, password=password).exists():
            b=tbl_Branch.objects.get(username=username, password=password)
            request.session['bch']=b.id
            return redirect("home")
    return render(request, "login.html")


def logout_view(request):
    if request.session.get("bch"):
        del request.session["bch"]
    else:
        logout(request)
    return redirect("login_view")

def admin_home(request):
    return render(request, "admin_home.html")

def branch_dashboard(request):
    return render(request, "branch_dashboard.html")

def branch(request):
    data=tbl_Branch.objects.all()
    context={
        "data": data,
    }
    return render(request, "branch.html",context)
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

from .models import LabBill


def bill_confirmation(request, bill_id):
    bill = get_object_or_404(LabBill, id=bill_id)

    # This URL must be publicly accessible for the patient's phone to open it.
    status_url = request.build_absolute_uri(
        reverse("patient-status", kwargs={"token": bill.status_token})
    )

    qr = qrcode.QRCode(box_size=8, border=3)
    qr.add_data(status_url)
    qr.make(fit=True)

    qr_image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    qr_image.save(buffer, format="PNG")

    qr_code = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return render(request, "bill_confirmation.html", {
        "bill": bill,
        "qr_code": qr_code,
        "status_url": status_url,
    })


def patient_status(request, token):
    bill = get_object_or_404(LabBill, status_token=token)

    # Display only the information the patient needs.
    return render(request, "patient_status.html", {
        "bill": bill,
    })


@require_POST
def send_waiting_sms(request, bill_id):
    bill = get_object_or_404(LabBill, id=bill_id)

    if not bill.phone or not bill.waiting_time:
        messages.error(
            request,
            "A valid patient phone number and waiting time are required."
        )
        return redirect("bill-confirmation", bill_id=bill.id)

    # Normalize an Indian mobile number.
    phone = "".join(ch for ch in bill.phone if ch.isdigit())

    if len(phone) == 12 and phone.startswith("91"):
        phone = phone[2:]

    if len(phone) != 10 or phone[0] not in "6789":
        messages.error(
            request,
            "Please check the patient's Indian mobile number."
        )
        return redirect("bill-confirmation", bill_id=bill.id)

    status_url = request.build_absolute_uri(
        reverse("patient-status", kwargs={"token": bill.status_token})
    )

    api_key = getattr(settings, "FAST2SMS_API_KEY", "")
    sender_id = getattr(settings, "FAST2SMS_SENDER_ID", "")
    message_id = getattr(settings, "FAST2SMS_MESSAGE_ID", "")

    if not all([api_key, sender_id, message_id]):
        messages.error(
            request,
            "SMS is not configured yet. Add your Fast2SMS API key, "
            "approved sender ID and approved message ID in settings."
        )
        return redirect("bill-confirmation", bill_id=bill.id)

    # Your approved DLT template must contain these three variables
    # in this exact order: patient name, waiting minutes, status URL.
    payload = {
        "route": "dlt",
        "sender_id": sender_id,
        "message": message_id,
        "variables_values": (
            f"{bill.patient_name}|{bill.waiting_time}|{status_url}"
        ),
        "numbers": phone,
    }

    try:
        response = requests.post(
            "https://www.fast2sms.com/dev/bulkV2",
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
                "accept": "application/json",
            },
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        result = response.json()

    except (requests.RequestException, ValueError):
        messages.error(
            request,
            "Could not confirm the SMS request. Please check the provider "
            "dashboard before trying again."
        )
        return redirect("bill-confirmation", bill_id=bill.id)

    if result.get("return") is True:
        bill.sms_sent_at = timezone.now()
        bill.save(update_fields=["sms_sent_at"])
        messages.success(
            request,
            "The SMS request was accepted by the provider."
        )
    else:
        messages.error(
            request,
            "The SMS provider rejected the request. "
            "Check your API settings and approved template."
        )

    return redirect("bill-confirmation", bill_id=bill.id)


