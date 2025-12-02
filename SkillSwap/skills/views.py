from django.shortcuts import render, redirect
from django.http import HttpRequest
from .forms import SkillForm

# Create your views here.

def add_skill_view(request: HttpRequest):

    if request.method == "POST":
        skill_form = SkillForm(request.POST, request.FILES)
        if skill_form.is_valid():
            skill_form.save()
            return redirect("skills:home_view")
    else:
        skill_form = SkillForm()

    return render(request, "skills/add_skill.html", {"skill_form": skill_form})