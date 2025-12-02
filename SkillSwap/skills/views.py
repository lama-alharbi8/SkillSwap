from django.shortcuts import render, redirect
from django.http import HttpRequest
from .forms import CategoryForm, SkillForm
from .models import Category, Skill
from django.db import transaction

# Create your views here.

def cat_skill_add(request):

    if request.method == 'POST':
        skill = request.POST.get('skill', '').strip()
        #nested categories
        level1 = request.POST.get('level1', '').strip()
        level2 = request.POST.get('level2', '').strip()
        level3 = request.POST.get('level3', '').strip()

        #will not save if user doesnt enter a skill
        if not skill:
            return render(request, "skills/cat_skill_add.html", {'error': 'Enter Skill Name'})

        with transaction.atomic():
            parent = None
            for lvl in (level1, level2, level3):
                if not lvl:
                    break
                #for no duplicates
                cat, created = Category.objects.get_or_create(category = lvl, parent = parent)
                #next level will be a child for this element
                parent = cat 

            skill, created = Skill.objects.get_or_create(skill = skill, defaults={'proficiency_level': Skill.ProficiencyLevel.BEGINNER})

            #relation between skill and last category level
            if parent:
                skill.categories.add(parent)

        return redirect("skills:cat_skill_add")

    return render(request, "skills/cat_skill_add.html")


