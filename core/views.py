from django import forms
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response

import datetime 
import json
from pymongo import Connection, objectid, ASCENDING
import re

#======= Helpers
class SearchForm(forms.Form):
    q = forms.CharField(max_length=100)

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
def connection():
    conn = Connection('localhost', 27017)
    db = conn.schools
    return db
    
def collection():
    db = connection()
    records = db.schools
    return records    
    
def get_district(building):
    records = collection()
    district = records.find_one({'District Code': building['District Code'], 'Building Code': '00000'})
    return district
    
def get_state():
    records = collection()
    state = records.find_one({"Statewide Record": True})
    return state
    
    
#======= Views
def home(request):
    response = {}
    
    schools = collection()
    buildings = schools.find({'Building Code': {'$ne':'00000'}})
    
    response['buildings'] = buildings
    
    response['search'] = SearchForm()

    return render_to_response('home.html', response)
    
    
def building(request, building_code):
    response = {}
    records = collection()
    
    building = records.find_one({'Building Code': building_code})
    response['building'] = dict(building)
    
    district = get_district(building)
    response['district'] = district
    
    state = get_state()
    response['state'] = state
    
    return render_to_response('building.html', response)
    
    
def district(request, district_code):
    response = {}
    records = collection()
    
    district = records.find_one({'District Code': district_code, 'Building Code': '00000'})
    response['district'] = dict(district)
    
    schools = records.find({'District Code': district_code, 'Building Code': {'$ne':'00000'}}).sort('Building Name')
    response['schools'] = schools
    
    return render_to_response('district.html', response)
        
        
def search(request):
    response = {}
    form = SearchForm()
    if request.method == 'GET': 
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['q']
            response['query'] = query
            
            all_records = collection()
            school_results = all_records.find({
                    "Building Name" : re.compile(query,re.IGNORECASE), 
                    'Building Code': {'$ne':'00000'}  
                },  
                sort = [('Building Name', ASCENDING)]
                )
            school_results = list(school_results)
            response['schools'] = school_results
            
            district_results = all_records.find({
                    "District Name" : re.compile(query,re.IGNORECASE), 
                    'Building Code': '00000'
                },
                sort = [('District Name', ASCENDING)]
                )
            
            district_results = list(district_results)
            response['districts'] = district_results            
                    
    response['form'] = form
    return render_to_response('search.html', response)


    
def search_json(request):
    if request.GET:
        query = request.GET['term']
        all_records = collection()
        
        school_results = all_records.find({
                "Building Name" : re.compile(query,re.IGNORECASE), 
                'Building Code': {'$ne':'00000'}  
            },  
            fields=['Building Name', 'Building Code'])
        
        cleaned_results = []
        for result in school_results:
            cleaned_results.append({'buildingname': result['Building Name'], 'buildingcode': result['Building Code']})
        return HttpResponse(json.dumps(cleaned_results), mimetype="application/json")
    