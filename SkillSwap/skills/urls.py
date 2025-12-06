from django.urls import path
from . import views

app_name = "skills"

urlpatterns = [
    
    path('add-category-skill/', views.cat_skill_add, name='cat_skill_add'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('offer-skill/', views.offer_skill, name='offer_skill'),
    path('need-skill/', views.need_skill, name='need_skill'),
    path('manage-offered-skills/', views.manage_offered_skills, name='manage_offered_skills'),
    path('manage-needed-skills/', views.manage_needed_skills, name='manage_needed_skills'),
    path('find-matches/', views.find_matches, name='find_matches'),
    path('initiate-exchange/<int:offered_skill_id>/', views.initiate_exchange, name='initiate_exchange'),
    path('propose-exchange/<int:needed_skill_id>/', views.propose_exchange, name='propose_exchange'),
    path('exchange/<int:exchange_id>/', views.exchange_detail, name='exchange_detail'),
    path('exchange/<int:exchange_id>/update-status/', views.update_exchange_status, name='update_exchange_status'),
    path('exchange/<int:exchange_id>/rate/', views.submit_rating, name='submit_rating'),
    path('chains/<int:chain_id>/', views.chain_detail, name='chain_detail'),
    path('chains/create/', views.create_chain, name='create_chain'),
    path('chains/<int:chain_id>/manage/', views.manage_chain, name='manage_chain'),
    path('chains/<int:chain_id>/join/', views.join_chain, name='join_chain'),
    path('chains/', views.exchange_chains, name='exchange_chains'),
    path('api/user-skills/', views.get_user_offered_skills, name='api_user_skills'),
    path('api/calculate-exchange/', views.calculate_fair_exchange_api, name='api_calculate_exchange'),
    path('api/potential-exchanges/', views.get_potential_exchanges, name='api_potential_exchanges'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.notification_mark_read, name='notification_mark_read'),
    path('api/notifications/count/', views.get_notifications_count, name='get_notifications_count'),
    path('statistics/', views.exchange_statistics, name='statistics'),
]


handler404 = views.handler404
handler500 = views.handler500