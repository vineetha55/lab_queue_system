
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

class Collection(models.Model):
    branch=models.ForeignKey(tbl_Branch, on_delete=models.CASCADE,null=True)
    patient_name = models.CharField(max_length=150)
    lab_number = models.CharField(max_length=50)
    phone = models.CharField(max_length=20, blank=True)
    purpose = models.TextField()
    
    urgent = models.BooleanField(default=False)
    note = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to="lab_bills/")
    ocr_text = models.TextField(blank=True)


from django.db import models


class CollectionSampleReceipt(models.Model):

    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name="sample_receipts"
    )

    sample_name = models.CharField(max_length=200)

    is_received = models.BooleanField(default=False)

    received_date = models.DateField(
        null=True,
        blank=True
    )

    received_time = models.TimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('collection', 'sample_name')
        ordering = ['id']

    def __str__(self):
        return f"{self.collection_id} - {self.sample_name}"
