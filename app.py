#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import (
  Flask, 
  render_template, 
  request, 
  Response, 
  flash, 
  redirect, 
  url_for
)
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from flask import Flask
from models import app, db, Venue, Artist, Show


app.config.from_object('config')
db.init_app(app)
moment = Moment(app)


app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

def get_shows(type, id):
  """
  This function gets the shows and (venue or artist) data depending
  on the type parameter and the id of either of them in the GET request
  """
  shows = {
    'upcoming_shows': [],
    'past_shows': [],
    'upcoming_shows_count': 0,
    'past_shows_count': 0
  }
  now = datetime.now()

  if type == 'artist':
    #Get the shows and venues data for the artist ID
    keys = ['artist_id', 'artist_name', 'artist_image_link', 'start_time']
    data = db.session.query(Show.artist_id, Artist.name, Artist.image_link, Show.start_time)\
    .join(Artist).join(Venue).filter(Venue.id == id).all()
  elif type == 'venue':
    #Get the shows and artists data for the venue ID
    keys = ['venue_id', 'venue_name', 'venue_image_link', 'start_time']
    data = db.session.query(Show.venue_id, Venue.name, Venue.image_link, Show.start_time)\
        .join(Venue).join(Artist).filter(Artist.id == id).all()

  for show in data:
    schema = {}
    for i in range(len(keys)):
      if i != 3:
        schema.update({keys[i]: show[i]})
      else:
        schema.update({keys[i]: show[3].strftime("%Y-%m-%d %H:%M:%S")})
    #set the upcoming or past show depending on the time of the select query
    if show[3] > now:
      shows['upcoming_shows'].append(schema)
      shows['upcoming_shows_count'] += 1
    else:
      shows['past_shows'].append(schema)
      shows['past_shows_count'] += 1

  #the next commented code does the same thing but harder to read 
  #and requires 2 queries to the db one for the upcoming shows and 1 for the past shows 
  #(I stopped at 1) but uses count aggregate and query filters


  # upcoming_shows = data.filter(Show.start_time > now)
  # for data in upcoming_shows.all():
  #   schema = {keys[i]: data[i] for i in range(len(keys))}
  #   shows['upcoming_shows'].append(schema)
  # shows['upcoming_shows_count] = upcoming_shows.count()

  # past_shows = data.filter(Show.start_time <= now)
  # for data in past_shows.all():
  #   schema = {keys[i]: data[i] for i in range(len(keys))}
  #   shows['past_shows'].append(schema)
  # shows['past_shows_count'] = past_shows.count()

  return shows
#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  venues = db.session.query(Venue.city, Venue.state).distinct().all()
  data = []
  counter = 0
  for i in venues:
    data.append({'city': i.city, 'state': i.state})
    venue = db.session.query(Venue.id, Venue.name).filter(Venue.city == i.city, Venue.state == i.state).all()
    data[counter].update({'venues': []})
    for j in venue:
      venue_info = {'id': j.id, 'name': j.name}
      data[counter]['venues'].append(venue_info)
    counter += 1
  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  # case insensitive search for venues with a matching string to the input
  response = {}
  response['data'] = Venue.query.filter(Venue.name.ilike("%" + request.form.get('search_term') + "%")).all()
  response['count'] = len(response['data'])
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  venue = Venue.query.get(venue_id)
  shows = get_shows('artist', venue_id)
  shows.update(vars(venue))
  return render_template('pages/show_venue.html', venue=shows)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  data=request.form
  try:
    new_venue = Venue(
      name=data['name'],
      city=data['city'],
      state=data['state'],
      address=data['address'],
      phone=data['phone'],
      genres=data.getlist('genres'),
      image_link=data['image_link'],
      facebook_link=data['facebook_link'],
      website=data['website'],
      seeking_talent= ("True" == data['seeking_talent']),
      seeking_description=data['seeking_description']
    )
    db.session.add(new_venue)
    db.session.commit()
    # on successful db insert, flash success
    flash('Venue ' + data['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    #on unsuccessful db insert, flash an error instead
    flash('An error occurred. Venue ' + data['name'] + ' could not be listed.')
  finally:
    db.session.close()
  return redirect(url_for('index'))
  
@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  try:
    Venue.query.filter_by(id=venue_id).delete()
    db.session.commit()
    # on successful db dekete, flash success
    flash('Venue was successfully deleted!')
  except:
    db.session.rollback()
    #on unsuccessful db insert, flash an error instead
    flash('An error occurred. Could not delete venue.')
  finally:
    db.session.close()
  return json.dumps({"redirect": "/venues"})

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = Artist.query.all()
  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  # case insensitive search for artists with a matching string to the input
  response= {}
  response['data'] = Artist.query.filter(Artist.name.ilike("%" + request.form.get('search_term') + "%")).all()
  response['count'] = len(response['data'])
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the venue page with the given venue_id
  artist = Artist.query.get(artist_id)
  shows = get_shows('venue', artist_id)
  shows.update(vars(artist))
  return render_template('pages/show_artist.html', artist=shows)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  # get the artist data to edit
  form = ArtistForm()
  artist = Artist.query.get(artist_id)
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # edit the artist data
  artist = Artist.query.get(artist_id)
  data = request.form
  try:
    artist = Artist.query.get(artist_id)
    artist.name = data['name']
    artist.city = data['city']
    artist.state = data['state']
    artist.phone = data['phone']
    artist.genres = data.getlist('genres')
    artist.image_link = data['image_link']
    artist.facebook_link = data['facebook_link']
    artist.website = data['website']
    artist.seeking_venue = ("True" == data['seeking_venue'])
    artist.seeking_description = data['seeking_description']
    db.session.add(artist)
    db.session.commit()
    # on successful db insert, flash success
    flash('Artist ' + data['name'] + ' was successfully updated!')
  except:
    db.session.rollback()
    #on unsuccessful db insert, flash an error instead
    flash('An error occurred. Artist ' + data['name'] + ' could not be updated.')
  finally:
    db.session.close()
  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  # get the venue data to edit
  form = VenueForm()
  venue = Venue.query.get(venue_id)
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # edit the venue data
  data = request.form
  try:
    venue = Venue.query.get(venue_id)
    venue.name = data['name']
    venue.city = data['city']
    venue.state = data['state']
    venue.address= data['address']
    venue.phone = data['phone']
    venue.genres = data.getlist('genres')
    venue.image_link = data['image_link']
    venue.facebook_link = data['facebook_link']
    venue.website = data['website']
    venue.seeking_talent = ("True" == data['seeking_talent'])
    venue.seeking_description = data['seeking_description']
    db.session.add(venue)
    db.session.commit()
    # on successful db insert, flash success
    flash('Venue ' + venue.name + ' was successfully edited!')
  except:
    db.session.rollback()
    #on unsuccessful db insert, flash an error instead
    flash('An error occurred. Venue ' + venue.name + ' could not be edited.')
  finally:
    db.session.close()
  return redirect(url_for('show_venue', venue_id = venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  data = request.form
  try:
    new_artist = Artist(
        name=data['name'],
        city=data['city'],
        state=data['state'],
        phone=data['phone'],
        genres=data.getlist('genres'),
        image_link=data['image_link'],
        facebook_link=data['facebook_link'],
        website=data['website'],
        seeking_venue= ("True" == data['seeking_venue']),
        seeking_description=data['seeking_description']
    )
    db.session.add(new_artist)
    db.session.commit()
    # on successful db insert, flash success
    flash('Artist ' + data['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    #on unsuccessful db insert, flash an error instead
    flash('An error occurred. Artist ' + data['name'] + ' could not be listed.')
  finally:
    db.session.close()
  return redirect(url_for('index'))

@app.route('/artists/<artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
  try:
    Artist.query.filter_by(id=artist_id).delete()
    db.session.commit()
    # on successful db dekete, flash success
    flash('Artist was successfully deleted!')
  except:
    db.session.rollback()
    #on unsuccessful db insert, flash an error instead
    flash('An error occurred. Could not delete artist.')
  finally:
    db.session.close()
  return json.dumps({"redirect": "/artists"})

#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  data = db.session.query(Show.artist_id, Show.venue_id, (Artist.name).label('artist_name'), (Artist.image_link).label('artist_image_link'), (Venue.name).label('venue_name'), Show.start_time).join(Venue).join(Artist).all()
  new_data = []
  for i in data:
    new_data.append(i._asdict())
  for j in new_data:
    j['start_time'] = j['start_time'].strftime("%Y-%m-%d %H:%M:%S")
  return render_template('pages/shows.html', shows=new_data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form
  data = request.form
  try:
    new_show = Show(
        artist_id=data['artist_id'],
        venue_id=data['venue_id'],
        start_time=datetime.strptime(data['start_time'], "%Y-%m-%d %H:%M:%S")
    )
    db.session.add(new_show)
    db.session.commit()
    # on successful db insert, flash success
    flash('Show was successfully listed!')
  except:
    db.session.rollback()
    # on unsuccessful db insert, flash an error instead.
    flash('An error occurred. Show could not be listed.')
  finally:
    db.session.close()
 
  return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
