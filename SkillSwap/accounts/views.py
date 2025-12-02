from django.shortcuts import render, redirect
from django.http import HttpRequest
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from skills.models import Skill, Category
from django.http import JsonResponse


# Create your views here.

def signup_view(request : HttpRequest):
    
    level1_categories = Category.objects.filter(parent__isnull=True)

    if request.method == "POST":
        try:
            new_user = User.objects.create_user(
                username = request.POST["username"],
                password = request.POST["password"],
                email = request.POST["email"],
                first_name = request.POST["first_name"],
                last_name = request.POST["last_name"],
            )
            new_user.save()
            
            skill_id = request.POST.get("skill")
            
            if skill_id:
                selected_skill = Skill.objects.get(id = skill_id)

            messages.success(request, "Registered User Successfully", "alert-success")
            return redirect("accounts:signin_view")
        except Exception as e: 
            print(e)
    
    return render(request, "accounts/signup.html", 
                  {
                    "level1_categories": level1_categories,
                      })


def signin_view(request : HttpRequest):
    
    if request.method == "POST":
        user = authenticate(request, username = request.POST["username"],
                password = request.POST["password"])
        
        if user:
            login(request, user)
            messages.success(request, "logged in successfuly", "alert-success")
            return redirect(request.GET.get("next", "/"))
        else:
            messages.error(request, "Please try again, your info is wrong", "alert-danger")
     
    return render(request, "accounts/signin.html", {})


def log_out_view(request : HttpRequest):
    
    logout(request)
    messages.success(request, "logged out successfuly", "alert-success")
    return redirect("main:home_view")


def category_children(request : HttpRequest, pk):
    try:
        parent = Category.objects.get(id=pk)
        children = parent.children.all()
        data = [{"id": c.id, "category": c.category} for c in children]
        return JsonResponse(data, safe=False)
    except Category.DoesNotExist:
        return JsonResponse([], safe=False)


def category_skills(request : HttpRequest, pk):
    try:
        category = Category.objects.get(id=pk)
        skills = category.skills.all()
        data = [{"id": s.id, "skill": s.skill} for s in skills]
        return JsonResponse(data, safe=False)
    except Category.DoesNotExist:
        return JsonResponse([], safe=False)