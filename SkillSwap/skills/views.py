from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from .notifications import send_exchange_notification, get_unread_notifications_count, get_recent_notifications, mark_all_as_read
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.utils import timezone
from .models import (
    Skill, OfferedSkill, NeededSkill, 
    SkillExchange, ExchangeChain, ChainLink, BrokerProposal,
    Notification  # ADDED THIS IMPORT
)
from .forms import (
    SkillForm, OfferSkillForm, NeedSkillForm, 
    ProposeExchangeForm, ExchangeProposalForm, ChainLinkForm
)
from django.db import transaction
import json
from datetime import timedelta
from decimal import Decimal
from django.db.models import Sum


# Create your views here.

@login_required
def cat_skill_add(request):
    
    if not request.user.is_staff:
        messages.success(request, "Only staff members can view this page")
        return redirect("accounts:sign_in")
    
    if request.method == 'POST':
        skill_name = request.POST.get('skill', '').strip()

        if not skill_name:
            return render(request, "skills/cat_skill_add.html", {'error': 'Enter Skill Name'})

        skill, created = Skill.objects.get_or_create(skill=skill_name)

        return redirect("skills:cat_skill_add")

    return render(request, "skills/cat_skill_add.html")


@login_required
def dashboard(request: HttpRequest):
    user = request.user

    context = {
        'user_offered_skills': OfferedSkill.objects.filter(user=user, is_active=True),
        'user_needed_skills': NeededSkill.objects.filter(user=user, is_active=True),
        'initiated_exchanges': SkillExchange.objects.filter(initiator=user).order_by('-created_at')[:5],
        'responded_exchanges': SkillExchange.objects.filter(responder=user).order_by('-created_at')[:5],
        'active_exchanges': SkillExchange.objects.filter(
            Q(initiator=user) | Q(responder=user), 
            status__in=['pending', 'under_review', 'negotiating', 'accepted', 'in_progress']
        ).order_by('-last_updated'),
        'completed_exchanges': SkillExchange.objects.filter(
            Q(initiator=user) | Q(responder=user), 
            status='completed'
        ).order_by('-completed_at')[:10],
        'exchange_chains': ExchangeChain.objects.filter(chain_links__user=user).distinct()[:5],
        'unread_notifications': get_unread_notifications_count(user), 
        'recent_notifications': get_recent_notifications(user, 5),     
    }

    return render(request, 'skills/dashboard.html', context)

@login_required
def offer_skill(request):
    if request.method == 'POST':
        form = OfferSkillForm(request.POST, user=request.user)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.user = request.user
            offer.save()
            messages.success(request, f'You are now offering {offer.skill.skill}!')
            return redirect('skills:dashboard')
    else:
        form = OfferSkillForm(user=request.user)
    
    context = {
        'form': form,
        'existing_offers': request.user.offered_skills.select_related('skill').all(),
    }
    return render(request, 'skills/offer_skill.html', context)

@login_required
def need_skill(request):
    if request.method == 'POST':
        form = NeedSkillForm(request.POST, user=request.user)
        if form.is_valid():
            need = form.save(commit=False)
            need.user = request.user
            need.save()
            messages.success(request, f'You are now requesting {need.skill.skill}!')
            return redirect('skills:dashboard')
    else:
        form = NeedSkillForm(user=request.user)
    
    context = {
        'form': form,
        'existing_needs': request.user.needed_skills.select_related('skill').all(),
    }
    return render(request, 'skills/need_skill.html', context)

@login_required
def manage_offered_skills(request):

    offered_skills = OfferedSkill.objects.filter(user=request.user)
    
    if request.method == 'POST' and 'toggle_active' in request.POST:
        skill_id = request.POST.get('skill_id')
        skill = get_object_or_404(OfferedSkill, id=skill_id, user=request.user)
        skill.is_active = not skill.is_active
        skill.save()
        messages.success(request, f'Skill {"activated" if skill.is_active else "deactivated"}!')
        return redirect('skills:manage_offered_skills')
    
    return render(request, 'skills/manage_offered_skills.html', {
        'offered_skills': offered_skills
    })

@login_required
def manage_needed_skills(request):

    needed_skills = NeededSkill.objects.filter(user=request.user)
    
    if request.method == 'POST' and 'toggle_active' in request.POST:
        skill_id = request.POST.get('skill_id')
        skill = get_object_or_404(NeededSkill, id=skill_id, user=request.user)
        skill.is_active = not skill.is_active
        skill.save()
        messages.success(request, f'Skill need {"activated" if skill.is_active else "deactivated"}!')
        return redirect('skills:manage_needed_skills')
    
    return render(request, 'skills/manage_needed_skills.html', {
        'needed_skills': needed_skills
    })

@login_required
def find_matches(request):
    """Find matching skills for user's needs and vice versa"""
    user = request.user
    

    matching_offers = []
    for need in NeededSkill.objects.filter(user=user, is_active=True):
        offers = OfferedSkill.objects.filter(
            is_active=True,
            skill=need.skill,
        ).exclude(user=user)
        
  
        if need.max_hourly_rate:
            offers = offers.filter(hourly_rate_equivalent__lte=need.max_hourly_rate)
        
        for offer in offers:
            matching_offers.append({
                'need': need,
                'offer': offer,
                'fairness_score': 100, 
                'match_type': 'skill_match'
            })
    

    matching_needs = []
    for offer in OfferedSkill.objects.filter(user=user, is_active=True):
        needs = NeededSkill.objects.filter(
            is_active=True,
            skill=offer.skill,
        ).exclude(user=user)
        
     
        needs = needs.filter(
            Q(max_hourly_rate__isnull=True) | 
            Q(max_hourly_rate__gte=offer.hourly_rate_equivalent)
        )
        
        for need in needs:
            matching_needs.append({
                'offer': offer,
                'need': need,
                'fairness_score': 100,  
                'match_type': 'need_match'
            })
    

    all_matches = matching_offers + matching_needs
    
    return render(request, 'skills/find_matches.html', {
        'matches': all_matches[:20],  
        'match_count': len(all_matches)
    })

@login_required
def initiate_exchange(request, offered_skill_id):
  
    target_skill = get_object_or_404(OfferedSkill, id=offered_skill_id, is_active=True)
    
    if target_skill.user == request.user:
        messages.error(request, "You cannot exchange with yourself!")
        return redirect('skills:dashboard')
    

    user_offered_skills = OfferedSkill.objects.filter(
        user=request.user,
        is_active=True
    )
    
    if request.method == 'POST':
   
        user_skill_id = request.POST.get('user_skill_id')
        user_skill = get_object_or_404(OfferedSkill, id=user_skill_id, user=request.user)
        
 
        exchange = SkillExchange.objects.create(
            initiator=request.user,
            responder=target_skill.user,
            skill_from_initiator=user_skill,
            skill_from_responder=target_skill,
            exchange_type='value',  
            status='pending',
            terms=request.POST.get('terms', '')
        )
        

        send_exchange_notification(exchange, 'exchange_proposed')
        
        messages.success(request, f'Exchange proposal sent to {target_skill.user.username}!')
        return redirect('skills:exchange_detail', exchange_id=exchange.id)
    
    return render(request, 'skills/initiate_exchange.html', {
        'target_skill': target_skill,
        'user_offered_skills': user_offered_skills
    })

@login_required
def propose_exchange(request, needed_skill_id):

    needed_skill = get_object_or_404(NeededSkill, id=needed_skill_id, is_active=True)
    
    if needed_skill.user == request.user:
        messages.error(request, "This is your own skill need!")
        return redirect('skills:dashboard')
    
    matching_skills = OfferedSkill.objects.filter(
        user=request.user,
        is_active=True,
        skill=needed_skill.skill
    )
    
    if not matching_skills.exists():
        messages.error(request, "You don't offer a skill that matches this need!")
        return redirect('skills:dashboard')
    

    initiator_offered_skills = OfferedSkill.objects.filter(
        user=needed_skill.user,
        is_active=True
    )
    
    if request.method == 'POST':
        user_skill_id = request.POST.get('user_skill_id')
        initiator_skill_id = request.POST.get('initiator_skill_id')
        
        if not user_skill_id or not initiator_skill_id:
            messages.error(request, "Please select skills from both parties!")
            return redirect('skills:propose_exchange', needed_skill_id=needed_skill_id)
        
        user_skill = get_object_or_404(OfferedSkill, id=user_skill_id, user=request.user)
        initiator_skill = get_object_or_404(OfferedSkill, id=initiator_skill_id, user=needed_skill.user)
        
        exchange = SkillExchange.objects.create(
            initiator=request.user,
            responder=needed_skill.user,
            skill_from_initiator=user_skill,
            skill_from_responder=initiator_skill, 
            exchange_type='value',
            status='pending',
            terms=request.POST.get('terms', ''),
            proposed_start_date=request.POST.get('proposed_start_date') or None,
            proposed_end_date=request.POST.get('proposed_end_date') or None,
        )
        

        send_exchange_notification(exchange, 'exchange_proposed')
        
        messages.success(request, f'Exchange proposal sent to {needed_skill.user.username}!')
        return redirect('skills:exchange_detail', exchange_id=exchange.id)
    
    return render(request, 'skills/propose_exchange.html', {
        'needed_skill': needed_skill,
        'matching_skills': matching_skills,
        'initiator_offered_skills': initiator_offered_skills 
    })

@login_required
def exchange_detail(request, exchange_id):

    exchange = get_object_or_404(SkillExchange, id=exchange_id)
    

    if not exchange.is_participant(request.user):
        messages.error(request, "You don't have permission to view this exchange.")
        return redirect('skills:dashboard')
    

    fairness_report = exchange.get_detailed_fairness_report()
    adjustment_suggestion = exchange.suggest_adjustment()
    

    can_cancel_statuses = ['pending', 'under_review', 'negotiating']
    
    context = {
        'exchange': exchange,
        'fairness_report': fairness_report,
        'adjustment_suggestion': adjustment_suggestion,
        'is_initiator': exchange.initiator == request.user,
        'is_responder': exchange.responder == request.user,
        'other_party': exchange.get_other_party(request.user),
        'can_cancel_statuses': can_cancel_statuses, 
    }
    
    return render(request, 'skills/exchange_detail.html', context)

@login_required
@require_POST
def update_exchange_status(request, exchange_id):

    exchange = get_object_or_404(SkillExchange, id=exchange_id)
    
    if not exchange.is_participant(request.user):
        messages.error(request, "Not authorized")
        return redirect('skills:exchange_detail', exchange_id=exchange.id)
    
    new_status = request.POST.get('status')
    
    old_status = exchange.status
    exchange.status = new_status
    

    now = timezone.now()
    if new_status == 'accepted' and not exchange.accepted_at:
        exchange.accepted_at = now

        send_exchange_notification(exchange, 'exchange_accepted')
        
    elif new_status == 'in_progress' and not exchange.started_at:
        exchange.started_at = now
        
    elif new_status == 'completed' and not exchange.completed_at:
        exchange.completed_at = now

        send_exchange_notification(exchange, 'exchange_completed')
        
    elif new_status == 'cancelled':
        exchange.completed_at = now

        send_exchange_notification(exchange, 'exchange_cancelled')
    
    exchange.save()
    
    messages.success(request, f'Exchange status updated to {new_status.replace("_", " ").title()}.')
    return redirect('skills:exchange_detail', exchange_id=exchange.id)

@login_required
@require_POST
def submit_rating(request, exchange_id):

    exchange = get_object_or_404(SkillExchange, id=exchange_id)
    
    if not exchange.is_participant(request.user):
        messages.error(request, "Not authorized")
        return redirect('skills:exchange_detail', exchange_id=exchange.id)
    
    if exchange.status != 'completed':
        messages.error(request, "Exchange not completed yet")
        return redirect('skills:exchange_detail', exchange_id=exchange.id)
    
    rating = request.POST.get('rating')
    feedback = request.POST.get('feedback', '')
    
    if request.user == exchange.initiator:
        exchange.initiator_rating = rating
        exchange.initiator_feedback = feedback
 
        send_exchange_notification(exchange, 'rating_received', to_user=exchange.responder)
    else:
        exchange.responder_rating = rating
        exchange.responder_feedback = feedback

        send_exchange_notification(exchange, 'rating_received', to_user=exchange.initiator)
    
    exchange.save()
    messages.success(request, 'Thank you for your rating!')
    return redirect('skills:exchange_detail', exchange_id=exchange.id)

@login_required
def chain_detail(request, chain_id):

    chain = get_object_or_404(ExchangeChain, id=chain_id)
    links = chain.chain_links.all().order_by('position')
    

    fairness_score = chain.calculate_fairness()
    
   
    user_link = links.filter(user=request.user).first()
    
    context = {
        'chain': chain,
        'links': links,
        'fairness_score': fairness_score,
        'user_link': user_link,
        'can_join': (
            chain.status in ['forming', 'proposed'] and 
            not user_link and
            chain.created_by != request.user
        ),
    }
    
    return render(request, 'skills/chain_detail.html', context)

@login_required
def create_chain(request):

    if request.method == 'POST':
        form = ExchangeProposalForm(request.POST)
        if form.is_valid():
            chain = form.save(commit=False)
            chain.created_by = request.user
            chain.status = 'forming'
            chain.save()
            
            messages.success(request, 'Exchange chain created! Start adding participants.')
            return redirect('skills:manage_chain', chain_id=chain.id)
    else:
        form = ExchangeProposalForm()
    
    return render(request, 'skills/create_chain.html', {'form': form})

@login_required
def manage_chain(request, chain_id):

    chain = get_object_or_404(ExchangeChain, id=chain_id, created_by=request.user)
    links = chain.chain_links.all().order_by('position')
    
    if request.method == 'POST':
        if 'add_participant' in request.POST:
            user_id = request.POST.get('user_id')
            gives_skill_id = request.POST.get('gives_skill_id')
            receives_skill_id = request.POST.get('receives_skill_id')
            
            user = get_object_or_404(User, id=user_id)
            gives_skill = get_object_or_404(OfferedSkill, id=gives_skill_id, user=user)
            receives_skill = get_object_or_404(OfferedSkill, id=receives_skill_id)
            

            ChainLink.objects.create(
                chain=chain,
                user=user,
                gives_skill=gives_skill,
                receives_skill=receives_skill,
                position=links.count(),
                status='pending'
            )
            
            messages.success(request, f'Added {user.username} to the chain.')
        
        elif 'remove_participant' in request.POST:
            link_id = request.POST.get('link_id')
            link = get_object_or_404(ChainLink, id=link_id, chain=chain)
            link.delete()
            messages.success(request, 'Participant removed from chain.')
        
        elif 'propose_chain' in request.POST:
            chain.status = 'proposed'
            chain.proposed_at = timezone.now()
            chain.save()
            
            messages.success(request, 'Chain proposed to all participants!')
        
        return redirect('skills:manage_chain', chain_id=chain.id)
    

    potential_users = User.objects.exclude(
        id__in=[link.user_id for link in links]
    ).exclude(id=request.user.id)
    
    return render(request, 'skills/manage_chain.html', {
        'chain': chain,
        'links': links,
        'potential_users': potential_users,
        'fairness_score': chain.calculate_fairness(),
    })

@login_required
@require_POST
def join_chain(request, chain_id):

    chain = get_object_or_404(ExchangeChain, id=chain_id)
    

    if chain.status not in ['forming', 'proposed']:
        messages.error(request, 'This chain is not open for new participants.')
        return redirect('skills:chain_detail', chain_id=chain.id)
    

    if chain.chain_links.filter(user=request.user).exists():
        messages.error(request, 'You are already in this chain.')
        return redirect('skills:chain_detail', chain_id=chain.id)
    

    gives_skill_id = request.POST.get('gives_skill_id')
    receives_skill_id = request.POST.get('receives_skill_id')
    
    if not gives_skill_id or not receives_skill_id:
        messages.error(request, 'Please specify both skills you give and receive.')
        return redirect('skills:chain_detail', chain_id=chain.id)
    
    gives_skill = get_object_or_404(OfferedSkill, id=gives_skill_id, user=request.user)
    receives_skill = get_object_or_404(OfferedSkill, id=receives_skill_id)

    ChainLink.objects.create(
        chain=chain,
        user=request.user,
        gives_skill=gives_skill,
        receives_skill=receives_skill,
        position=chain.chain_links.count(),
        status='pending'
    )
    
    messages.success(request, 'You have joined the exchange chain!')
    return redirect('skills:chain_detail', chain_id=chain.id)

@login_required
def exchange_chains(request):


    user_chains = ExchangeChain.objects.filter(
        chain_links__user=request.user
    ).distinct().order_by('-created_at')
    

    public_chains = ExchangeChain.objects.filter(
        status__in=['forming', 'proposed']
    ).exclude(
        chain_links__user=request.user
    ).distinct().order_by('-created_at')
    
    context = {
        'user_chains': user_chains,
        'public_chains': public_chains,
    }
    
    return render(request, 'skills/exchange_chains.html', context)

@login_required
def notifications(request):

    notifications_list = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_count = get_unread_notifications_count(request.user)
    

    if request.GET.get('mark_read'):
        mark_all_as_read(request.user)
        messages.success(request, 'All notifications marked as read!')
        return redirect('skills:notifications')
    
    return render(request, 'skills/notifications.html', {
        'notifications': notifications_list,
        'unread_count': unread_count,
    })

@login_required
def notification_mark_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
 
    if notification.content_object:
        if isinstance(notification.content_object, SkillExchange):
            return redirect('skills:exchange_detail', exchange_id=notification.content_object.id)
    
    return redirect('skills:notifications')

@login_required
def get_notifications_count(request):
    """API endpoint to get unread notifications count (for AJAX)"""
    count = get_unread_notifications_count(request.user)
    return JsonResponse({'count': count})



@login_required
def get_user_offered_skills(request):

    skills = OfferedSkill.objects.filter(
        user=request.user,
        is_active=True
    ).values('id', 'skill__skill', 'hourly_rate_equivalent')
    
    return JsonResponse(list(skills), safe=False)

@login_required
def calculate_fair_exchange_api(request):

    skill1_id = request.GET.get('skill1_id')
    skill2_id = request.GET.get('skill2_id')
    
    if not skill1_id or not skill2_id:
        return JsonResponse({'error': 'Missing skill IDs'}, status=400)
    
    skill1 = get_object_or_404(OfferedSkill, id=skill1_id)
    skill2 = get_object_or_404(OfferedSkill, id=skill2_id)
    

    temp_exchange = SkillExchange(
        skill_from_initiator=skill1,
        skill_from_responder=skill2,
    )
    
    result = temp_exchange.calculate_fair_exchange()
    
    if result:
        return JsonResponse({
            'success': True,
            'data': result,
            'skill1_rate': float(skill1.hourly_rate_equivalent),
            'skill2_rate': float(skill2.hourly_rate_equivalent),
        })
    else:
        return JsonResponse({
            'success': False,
            'error': 'Could not calculate fair exchange'
        })

@login_required
def get_potential_exchanges(request):

    user = request.user

    user_offers = OfferedSkill.objects.filter(user=user, is_active=True)
    

    matches = []
    for offer in user_offers:
        matching_needs = NeededSkill.objects.filter(
            is_active=True,
            skill=offer.skill,
        ).exclude(user=user)
        
        for need in matching_needs:

            if need.max_hourly_rate and offer.hourly_rate_equivalent > need.max_hourly_rate:
                continue
            
            matches.append({
                'type': 'need_match',
                'offer': {
                    'id': offer.id,
                    'skill': offer.skill.skill,
                    'rate': float(offer.hourly_rate_equivalent),
                },
                'need': {
                    'id': need.id,
                    'skill': need.skill.skill,
                    'user': need.user.username,
                    'urgency': need.urgency,
                },
                'match_score': 85, 
            })
    
    return JsonResponse({'matches': matches[:10]})



@login_required
def exchange_statistics(request):

    if not request.user.is_staff:
        messages.error(request, 'Access denied.')
        return redirect('skills:dashboard')
    

    total_exchanges = SkillExchange.objects.count()
    completed_exchanges = SkillExchange.objects.filter(status='completed').count()
    pending_exchanges = SkillExchange.objects.filter(status='pending').count()
    

    exchanges_with_score = SkillExchange.objects.exclude(
        initiator_hourly_rate=0,
        responder_hourly_rate=0
    )
    total_fairness = sum([e.get_fairness_score() for e in exchanges_with_score])
    avg_fairness = total_fairness / exchanges_with_score.count() if exchanges_with_score.count() > 0 else 0
    

    from django.db.models import Count
    popular_skills = Skill.objects.annotate(
        exchange_count=Count('offered_by_users__exchanges_as_offer') + 
                       Count('offered_by_users__exchanges_as_response')
    ).order_by('-exchange_count')[:10]
    
    context = {
        'total_exchanges': total_exchanges,
        'completed_exchanges': completed_exchanges,
        'pending_exchanges': pending_exchanges,
        'avg_fairness': round(avg_fairness, 1),
        'popular_skills': popular_skills,
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(
            offered_skills__is_active=True
        ).distinct().count(),
    }
    
    return render(request, 'skills/statistics.html', context)

def handler404(request, exception):

    return render(request, 'skills/404.html', status=404)

def handler500(request):

    return render(request, 'skills/500.html', status=500)