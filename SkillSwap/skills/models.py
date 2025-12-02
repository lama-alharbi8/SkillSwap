from django.db import models

# Create your models here.

class Skill(models.Model):
    
    skill = models.CharField(max_length = 128, unique = True)
    
    def __str__(self) -> str:
        return self.skill