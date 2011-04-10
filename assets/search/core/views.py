from core.models import School
from django import forms
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response

import datetime 
import json
import re

#======= Helpers
class SearchForm(forms.Form):
    term = forms.CharField(max_length=100)

'''
school record:
    building code
    building name
    district code
    district name
    
    year:
        dataset:
            record:
                name
                value
                explainer
            record
            record
'''

    
def get_district(building):
    records = collection()
    district = records.find_one({'District Code': building['District Code'], 'Building Code': '00000'})
    return district
    
def get_state():
    records = collection()
    state = records.find_one({"Statewide Record": True})
    return state
    
    
#======= Views
        
def search(request):
    context ={}
    form = SearchForm()
    if request.method == 'GET': 
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['term']
            context['query'] = query
                    
            #school_results = all_records.find({
            #        "Building Name" : re.compile(query,re.IGNORECASE), 
            #        'Building Code': {'$ne':'00000'}  
            #    },  
            #    sort = [('Building Name', ASCENDING)]
            #    )
            school_results = School.objects.filter(building_name__icontains=query).exclude(district_code='00000').order_by('building_name')
            context['schools'] = list(school_results)
            
            district_results = School.objects.filter(district_name__icontains=query, building_code="00000").order_by('district_name')
            context['districts'] = list(district_results)            
                    
    context['form'] = form
    return render_to_response('search.html', context)


    
def search_json(request):
    if request.GET:
        context = {}
        query = request.GET['term']
        
        school_results = School.objects.filter(building_name__icontains=query).exclude(district_code='00000').order_by('building_name')
        context['schools'] = list(school_results)
        
        cleaned_results = []
        for result in school_results:
            print result.building_code
            cleaned_results.append({
                'buildingname': result.building_name, 
                'buildingcode': result.building_code, 
                'districtcode': result.district_code,
                'url': '/building/' + result.building_code
            })
        return HttpResponse(json.dumps(cleaned_results), mimetype="application/json")
    