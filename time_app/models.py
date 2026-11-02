
from django.db import models
import uuid
class tbl_Branch(models.Model):
   name = models.CharField(max_length=150, blank=True)
   email = models.EmailField(max_length=150, blank=True)
   address = models.CharField(max_length=150, blank=True)
   phone = models.CharField(max_length=150, blank=True)
   username=models.CharField(max_length=150, blank=True)
   password = models.CharField(max_length=150, blank=True)
   created_at = models.DateTimeField(auto_now_add=True)
   def __str__(self):
       return f"{self.name} - {self.email}"

class LabBill(models.Model):
    branch=models.ForeignKey(tbl_Branch, on_delete=models.CASCADE,null=True)
    patient_name = models.CharField(max_length=150)
    lab_number = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True)

    purpose = models.CharField(max_length=50)

    waiting_time = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    urgent = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    image = models.ImageField(upload_to="lab_bills/")
    ocr_text = models.TextField(blank=True)
    status_token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    sms_sent_at = models.DateTimeField(null=True, blank=True)
    timer_stopped = models.BooleanField(default=False)
    timer_stopped_at = models.DateTimeField(null=True, blank=True)


class LabCollection(models.Model):

    bill = models.ForeignKey(
        LabBill,
        on_delete=models.CASCADE,
        related_name="collections"
    )

    test_name = models.CharField(max_length=150)

    called_at = models.DateTimeField(
        null=True,
        blank=True
    )

    inside_at = models.DateTimeField(
        null=True,
        blank=True
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    collector_name = models.CharField(
        max_length=150,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.bill.lab_number} - {self.test_name}"

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["bill", "test_name"],
                name="unique_test_per_bill"
            )
        ]



