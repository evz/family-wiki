"""
Entities blueprint for browsing database entities
"""

from flask import Blueprint, render_template

from web_app.database.models import Event, Family, Marriage, Person, Place
from web_app.services.extraction_service import extraction_service
from web_app.shared.logging_config import get_project_logger


logger = get_project_logger(__name__)

entities = Blueprint('entities', __name__, url_prefix='/entities')


@entities.route('/')
def index():
    """Browse all entities in the database"""
    db_stats = extraction_service.get_database_stats()
    return render_template('entities/index.html', db_stats=db_stats)


@entities.route('/persons')
def persons_list():
    """List all persons in the database"""
    persons = Person.query.order_by(Person.surname, Person.given_names).all()
    return render_template('entities/persons.html', persons=persons)


@entities.route('/persons/<person_id>')
def person_detail(person_id):
    """Show detailed view of a specific person"""
    person = Person.query.get_or_404(person_id)
    return render_template('entities/person_detail.html', person=person)


@entities.route('/families')
def families_list():
    """List all families in the database"""
    families = Family.query.order_by(Family.generation_number, Family.family_identifier).all()
    return render_template('entities/families.html', families=families)


@entities.route('/families/<family_id>')
def family_detail(family_id):
    """Show detailed view of a specific family"""
    family = Family.query.get_or_404(family_id)
    return render_template('entities/family_detail.html', family=family)


@entities.route('/places')
def places_list():
    """List all places in the database"""
    places = Place.query.order_by(Place.name).all()
    return render_template('entities/places.html', places=places)


@entities.route('/places/<place_id>')
def place_detail(place_id):
    """Show detailed view of a specific place"""
    place = Place.query.get_or_404(place_id)
    return render_template('entities/place_detail.html', place=place)


@entities.route('/events')
def events_list():
    """List all events in the database"""
    events = Event.query.order_by(Event.date, Event.title).all()
    return render_template('entities/events.html', events=events)


@entities.route('/events/<event_id>')
def event_detail(event_id):
    """Show detailed view of a specific event"""
    event = Event.query.get_or_404(event_id)
    return render_template('entities/event_detail.html', event=event)


@entities.route('/marriages')
def marriages_list():
    """List all marriages in the database"""
    marriages = Marriage.query.order_by(Marriage.marriage_date).all()
    return render_template('entities/marriages.html', marriages=marriages)


@entities.route('/marriages/<marriage_id>')
def marriage_detail(marriage_id):
    """Show detailed view of a specific marriage"""
    marriage = Marriage.query.get_or_404(marriage_id)
    return render_template('entities/marriage_detail.html', marriage=marriage)
