from django.db import models

# Create your models here.

class Category(models.Model):
    
    category = models.CharField(max_length = 128, unique = True)
    
    parent = models.ForeignKey(
        'self', 
        null = True, 
        blank = True, 
        related_name = 'children', 
        on_delete = models.CASCADE
    )
    
    def __str__(self) -> str:
        return self.category
    
    def get_full_path(self):
        full_path = [self.category]
        k = self.parent
        while k is not None:
            full_path.append(k.category)
            k = k.parent
        return ' > '.join(full_path[::-1])

class Skill(models.Model):
    class ProficiencyLevel(models.TextChoices):
        BEGINNER = 'Beginner',
        INTERMEDIATE = 'Intermediate',
        EXPERT = 'Expert',
        
    skill = models.CharField(max_length = 128, unique = True)
    proficiency_level = models.CharField(
        max_length = 64, 
        choices = ProficiencyLevel.choices,
        default = ProficiencyLevel.BEGINNER
        )
    categories = models.ManyToManyField(Category, related_name = 'skills', blank = True)
    
    def __str__(self) -> str:
        return self.skill
    