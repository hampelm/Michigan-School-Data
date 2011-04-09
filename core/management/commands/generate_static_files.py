import os 

from django import forms
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render_to_response
from django.template.loader import render_to_string

from core.views import connection, collection, get_district, get_state

from pymongo import Connection, objectid, ASCENDING


def render_to_file(template, filename, context):
    open(filename, "w").write(render_to_string(template, context))
    

class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def handle(self, *args, **options):
        static_file_base = os.path.join(settings.PROJECT_PATH, 'assets')
        state = get_state()
        records = collection()
        
        # find all districts & generate a static page for each
        districts = records.find({'Building Code': '00000', 'Statewide Record': {'$ne': True}})
        for district in districts:
            context = {}
            context['schools'] = records.find({'District Code': district['District Code'], 'Building Code': {'$ne': '00000'}})
            context['district'] = district

            context['state'] = state
            
            # make the directory
            try:
                district_directory = os.path.join(static_file_base, 'district/')
                district_directory = os.path.join(district_directory, district['District Code'])
                os.mkdir(district_directory)
            except:
                pass
            print district_directory
            
            # save the file as index.html
            render_to_file('district.html', os.path.join(district_directory, 'index.html'), context)

        
        # find all buildings & generate a static page for each
        schools = records.find({'Building Code': {'$ne':'00000'}, 'Statewide Record': {'$ne': True}})
        for building in schools:
            context = {}
            records = collection()

            context['building'] = dict(building)

            district = get_district(building)
            context['district'] = district

            context['state'] = state
            
            # make the directory
            
            try:
                building_directory = os.path.join(static_file_base, 'building/')
                building_directory = os.path.join(building_directory, building['Building Code'])
                os.mkdir(building_directory)
            except:
                pass
            print building_directory
            
            # save the file as index.html
            render_to_file('building.html', os.path.join(building_directory, 'index.html'), context)
            
            
