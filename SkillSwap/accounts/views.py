from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpRequest
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from skills.models import Skill, Category, OfferedSkill, NeededSkill  
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import UserProfile

import json
from django.utils.safestring import mark_safe

# Create your views here.

def signup_view(request : HttpRequest):
    
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

            messages.success(request, "Registered User Successfully", "alert-success")
            return redirect("accounts:signin_view")
        except Exception as e: 
            print(e)
    
    return render(request, "accounts/signup.html")
              
              
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
    
    
def profile_form(request : HttpRequest):
    
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    
    all_skills = Skill.objects.order_by('skill')
    all_skills_data = list(all_skills.values('id', 'skill'))
    all_skills_json = mark_safe(json.dumps(list(all_skills_data)))

    if request.method == "POST":
        bio = request.POST.get("bio", "").strip()
        avatar = request.FILES.get("avatar")

        profile.bio = bio
        if avatar:
            profile.avatar = avatar
        profile.save()
        
        
        offered_ids = [int(x) for x in request.POST.getlist("offered_skills") if x]
        needed_ids  = [int(x) for x in request.POST.getlist("needed_skills") if x]

        OfferedSkill.objects.filter(user=request.user).delete()
        NeededSkill.objects.filter(user=request.user).delete()


        offered_objs = []
        for sid in offered_ids:
            try:
                Skill.objects.get(id=sid)
                offered_objs.append(OfferedSkill(user=request.user, skill_id=sid))
            
            except (Skill.DoesNotExist, ValueError):
                continue

        needed_objs = []
        for sid in needed_ids:
            try:
                Skill.objects.get(id=sid)
                needed_objs.append(NeededSkill(user=request.user, skill_id=sid))
            
            except (Skill.DoesNotExist, ValueError):
                continue

        if offered_objs:
            OfferedSkill.objects.bulk_create(offered_objs)
        if needed_objs:
            NeededSkill.objects.bulk_create(needed_objs)
            
        return redirect("accounts:profile_form")

    current_offered = list(Skill.objects.filter(offered_by_users__user=request.user).values_list('id', flat=True))
    current_needed  = list(Skill.objects.filter(needed_by_users__user=request.user).values_list('id', flat=True))


    current_offered_json = mark_safe(json.dumps(list(current_offered)))
    current_needed_json  = mark_safe(json.dumps(list(current_needed)))


    return render(request, "accounts/profile_form.html", {
        "profile": profile,
        "all_skills": all_skills,
        "all_skills_data": all_skills_data,
        "all_skills_json": all_skills_json,
        "current_offered": current_offered,
        "current_needed": current_needed,
        "current_offered_json": current_offered_json,
        "current_needed_json": current_needed_json,
    })
    
    
@login_required
def user_profile(request : HttpRequest):    
    
    profile = get_object_or_404(UserProfile.objects.select_related('user'), user=request.user)

    offered = profile.user.offered_skills.select_related('skill').filter(is_active=True)
    needed  = profile.user.needed_skills.select_related('skill').filter(is_active=True)

    return render(request, 'accounts/user_profile.html', {
        'profile': profile,
        'offered_skills': offered,
        'needed_skills': needed,
    })
    

def skills_search(request : HttpRequest):
    """
    AJAX endpoint: GET ?q=term
    Returns JSON list of matching skills: [{id, name}, ...]
    """
    q = request.GET.get('q', '').strip()
    qs = Skill.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
    qs = qs.order_by('name')[:30] 
    data = [{"id": s.id, "name": s.name} for s in qs]
    return JsonResponse({"results": data})
