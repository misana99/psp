from django.db import models

# Create your models here.
class Test(models.Model):
    activity = models.CharField(max_length=20)
    status = models.CharField(max_length=30)
    requested = models.DateField(auto_created=True)

    def __str__(self):
        return self.activity
