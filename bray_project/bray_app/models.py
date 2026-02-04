from django.db import models

# Create your models here.

class Alarm(models.Model):
    id = models.AutoField(primary_key=True, db_column='ID')
    alarm_code = models.CharField(max_length=50, unique=True, db_column='ALARM_ID')
    alarm_name = models.CharField(max_length=200, db_column='ALARM_NAME')
    created_at = models.DateTimeField(auto_now_add=True, db_column='CREATED_AT')
    updated_at = models.DateTimeField(auto_now=True, db_column='UPDATED_AT')
    
    class Meta:
        db_table = 'alarm'
        
    def __str__(self):
        return f"{self.alarm_code} - {self.alarm_name}"
