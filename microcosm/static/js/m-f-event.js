/////////
// MAP //
/////////

// Create map
var map;

// marker is a global, if it's populated then there is a marker on the map
var marker;

// Given an L.LatLng() as an argument will drop a pin on the map (removing
// any existing pin first), and then save the new lat:lng and maps bounds
function dropMarker(latLng) {
	if (marker) {
		map.removeLayer(marker);
	}

	marker = L.marker(latLng);
	map.addLayer(marker);

	saveLocationState(latLng);
}

// If a user wants to find a place on the map
$('#locate').bind('click', function() {
	// And they have entered it into the 'where' field
	var place = $.trim($('#id_where').val());
	if (place == '') {return;}

	// Then look it up
	var geoCodeUrl = '/geocode/?q=' + place;
	$.getJSON(geoCodeUrl, function(data) {
		// And if it's not found, show an error
		if (!data.found) {
			$('#control_where').addClass('has-error');
			$('#locate').removeClass('btn-info').addClass('btn-danger');
			return;
		}

		// Otherwise get the location
		var p = data.features[0];

		// Zoom to where it is
		map.fitBounds(p.bounds);

		// And drop a pin
		dropMarker(new L.LatLng(p.centroid.coordinates[0], p.centroid.coordinates[1]));
	});
});

// And if the user wants to change the 'where' independent of updating the
// pin, then that's cool
$('#id_where').bind('change', function() {

	// Unless they remove the label but have left a marker as a place should
	// have a name
	if (marker && $('#id_where').val().trim() != '') {
		// And that's an error
		$('#control_where').removeClass('has-error');
		$('#locate').removeClass('btn-danger').addClass('btn-info');
	}
});

// Given an L.LatLng, work out al the details and populate the form
function saveLocationState(latLng) {
	// Presume things are good
	$('#control_where').removeClass('has-error');
	$('#locate').removeClass('btn-danger').addClass('btn-info');

	// Unless they're not
	if (marker && $('#id_where').val().trim() == '') {
		// As the user is dropping a pin on the map without a label
		// for it
		$('#control_where').addClass('has-error');
		$('#locate').removeClass('btn-info').addClass('btn-danger');
		return
	}

	// Get the bounds (map box)
	var b = map.getBounds();
	var sw = b.getSouthWest();
	var ne = b.getNorthEast();
	
	// Save all the things!
	$('#id_lat').val(latLng.lat);
	$('#id_lon').val(latLng.lng);
	$('#id_north').val(ne.lat);
	$('#id_east').val(ne.lng);
	$('#id_south').val(sw.lat);
	$('#id_west').val(sw.lng);
}

// If this is the edit screen and we need to set the map to known values then
// we do so here
function restoreLocationState(lat, lng, bounds) {
	map.fitBounds(bounds);
	// Bounds will always be 1 level too far out due to imprecision in the
	// numbers and Leaflet aggressively ensuring the bounds fit inside the
	// map area. To prevent us slowly zooming out with each edit, we zoom in
	map.zoomIn();
	dropMarker(new L.LatLng(lat, lng));
}

///////////
// DATES //
///////////

// These are globals, if populated we believe the form is populated
var startDate = false;
var endDate = false;

// Very basic test regex of dates between 2010-01-01 and 2059-12-31 which is
// only here as a sanity check against manually entered input
var dateReg = /^20[1-5][0-9]-(0[1-9]|1[0-2])-([0][1-9]|[1-2][0-9]|3[0-1])$/

// The datepicker widget produces dates in "YYYY-MM-DD" format, and this
// converts that to a date object or returns false if the string was gibberish
function getDateFromIsoString(s) {
	var d = false;
	if (s.match(dateReg)) {
		var ds = s.split("-");
		d = new Date(Date.UTC(ds[0],ds[1]-1,ds[2]));
	}
	return d;
}

// The reverse of the above, if we have a date object then make a "YYYY-MM-DD"
// string
function getIsoStringFromDate(d) {
	var s = '';
	if (d) {
		var dd = d.getUTCDate();
		var mm = d.getUTCMonth() + 1;
		s = '' + d.getUTCFullYear() + '-' +
			(mm <= 9 ? '0' + mm : mm) + '-' +
			(dd <= 9 ? '0' + dd : dd);
	}
	return s;
}

// Given a valid date, set the global value and update the form.
// Given an invalid date, clear the value and form.
function setStartDate(d) {
	if (!d) {
		$('#id_from_date').val('');
		startDate = false;
		return;
	}
	$('#id_from_date').val(getIsoStringFromDate(d));
	$('#id_from_date').datepicker('update');
	startDate = d;
	validateDateTimes();
}

// Likewise for end date
function setEndDate(d) {
	if (!d) {
		$('#id_to_date').val('');
		endDate = false;
		return;
	}
	$('#id_to_date').val(getIsoStringFromDate(d));
	$('#id_to_date').datepicker('update');
	endDate = d;
	validateDateTimes();
}

//////////
// TIME //
//////////

// Add a time that is within a string in the format "03:45 PM" onto an existing
// date object
function setTime(d, ts) {
	if (!d) {return;}
	var time = ts.match(/(\d?\d):(\d\d)\s(P?)/);
	d.setHours(parseInt(time[1]) + ((parseInt(time[1]) < 12 && time[3]) ? 12 : 0));
	d.setMinutes(parseInt(time[2]) || 0);
}

// Given a date object, return the time formatted as "03:45 PM"
function getTimeStringFromDate(d) {
	var hh = d.getUTCHours();
	var mi = d.getUTCMinutes();
	var pm = (hh > 12);
	return '' + (hh <= 9 ? '0' + hh : (hh > 12 ? hh - 12: hh)) + ':' + 
		(mi <= 9 ? '0' + mi : mi) + ' ' +
		(pm ? 'PM' : 'AM');
}

// Not all browsers know how to do toISOString() as it was only added in
// ECMAScript 5, so we just ship our own version.
function dateToUtcString(d) {
	function pad(n) { return n < 10 ? '0' + n : n }
	return d.getUTCFullYear() + '-'
		+ pad(d.getUTCMonth() + 1) + '-'
		+ pad(d.getUTCDate()) + 'T'
		+ pad(d.getUTCHours()) + ':'
		+ pad(d.getUTCMinutes()) + ':'
		+ pad(d.getUTCSeconds()) + 'Z';
}

// Duration is a global and stores the difference between (startDate + startTime)
// and (endDate + endTime), expressed in minutes. So 180 = 3 hours difference.
var duration = 0;

// If everything checks out
function validateDateTimes() {
	var startTime = $('#id_from_time').val().trim();
	var endTime = $('#id_to_time').val().trim();

	// By which we mean, if we have all of the values
	if (!startDate || !endDate || !startTime || !endTime) {
		return false;
	}

	// We can glue them together
	var startDateTime = startDate;
	setTime(startDateTime, startTime);

	var endDateTime = endDate;
	setTime(endDateTime, endTime);

	// To calculate the difference between the dateTimes as an integer
	// representing minutes
	duration = (endDateTime.valueOf() / 60000) - (startDateTime.valueOf() / 60000);

	// And if we've got junk input, default to an hour
	if (!duration) {duration = 60;}

	// Save all the things!
	$('#id_duration').val(duration);
	$('#id_when').val(dateToUtcString(startDateTime));

	if ($('#id_where').val().trim() != '' && $('#id_lat').val().trim() == '') {
		// where text without pinned location
		return false;
	}

	if ($('#id_where').val().trim() == '' && $('#id_lat').val().trim() != '') {
		// pinned location without where text
		return false;
	}

	return true;
}

///////////////
// ATTENDEES //
///////////////

// Let's just make sure it's a number...
$('#id_rsvpLimit').bind('change', function() {
	rsvp = $(this);
	// Not empty, unparseable, or below zero?
	if (rsvp.val().trim() == '' || !parseInt(rsvp.val(), 10) || parseInt(rsvp.val(), 10) < 0) {
		rsvp.val('0');
	} else {
		// Cool, but if they've entered something funny let's clean it
		rsvp.val(parseInt(rsvp.val(), 10).toString(10));
	}
});

////////////////////
// INITIALISATION //
////////////////////
function loadForm() {
	// We're basically going to see what we have and set the state of the UI
	// appropriately. We don't know whether we're the create or edit form, so
	// let's just be sensible and do sensible things

	// STart by creating the widgets and binding their events
	map = L.map('map')
		.setMaxBounds([[-90,-180],[90,180]]); // Restrict map to valid lat:lng pairs

	// Using tiles from Cloudmade as they're pretty
	L.tileLayer(
		'https://d1qte70nkdppk5.cloudfront.net/d6f1a0c60e9746faa7cbfaec4b92dff3/997/256/{z}/{x}/{y}.png',
		{
			attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, Imagery © <a href="http://cloudmade.com">CloudMade</a>',
			minZoom: 0, // Zoom to world
			maxZoom: 18 // Zoom to finest detail
		}
	).addTo(map);

	// If a user manually wants to refine the pin point by clicking/touching
	// the map, then they can
	map.on('click', function(e) {
		dropMarker(e.latlng);
	});

	// If a user wants to manually refine the portion of the map on show, then
	// that's cool and we have the new zoom level and bounds
	map.on('moveend', function(e) {
		if (marker) {
			latLng = marker.getLatLng()
			saveLocationState(latLng);
		}
	});

	$('#id_from_date')
		// Create the date picker for the start date
		// http://xkcd.com/1179/
		.datepicker({format: 'yyyy-mm-dd'})
		// Detect not-null changes in the value
		.on('changeDate', function(ev){
			// If the end is before the start
			if (endDate && ev.date.valueOf() > endDate.valueOf()){
				// Then set the end to be the same as the start
				setStartDate(new Date(ev.date));
				$('#id_to_date').val($('#id_from_date').val());
			} else {
				// Else all is good and just set the start
				$('#control_from_date').removeClass('has-error');
				$('#control_to_date').removeClass('has-error');
				setStartDate(new Date(ev.date));
			}

			// Prevent the user from trying to select an end date prior to
			// the start date
			$('#id_to_date').datepicker('setStartDate', $('#id_from_date').val());

			// The user is done, hide the picker
			$('#id_from_date').datepicker('hide');
		})
		// Detect null changes
		.on('change', function() {
			// So that if they nuke the field, we put in tomorrow's date
			if ($('#id_from_date').val().trim() == '') {
				var d = new Date()
				d.setDate(d.getDate() + 1);
				setStartDate(d);
			}
		});

	$('#id_to_date')
		// Create the date picker for the end date
		.datepicker({format: 'yyyy-mm-dd'})
		// Detect not-null changes in the value
		.on('changeDate', function(ev){
			if (startDate && ev.date.valueOf() < startDate.valueOf()){
				// Ideally not possible due to restriction of interface and
				// preventing the end date picker having a value earlier than
				// the start date... but *if* the user has managed to select
				// a date earlier than start, then show an error and wipe
				// this erroneous value
				$('#control_from_date').addClass('has-error');
				$('#control_to_date').addClass('has-error');
				setEndDate(false);
			} else {
				// All is good, set the end
				$('#control_from_date').removeClass('has-error');
				$('#control_to_date').removeClass('has-error');
				setEndDate(new Date(ev.date));
			}

			// The user is done, hide the picker
			$('#id_to_date').datepicker('hide');
		})
		// Detect null changes
		.on('change', function() {
			// So that if they nuke the field, we put in the same as the start
			// date
			if ($('#id_to_date').val().trim() == '') {
				$('#id_to_date').val($('#id_from_date').val());
				setEndDate(getDateFromIsoString($('#id_from_date').val()));
			}
		});

	// Django defaults to spitting out 'None' in fields that have no value.
	// There is probably an idiomatic Django way to not do this, but I don't
	// know it and this is as effective
	$('input[value="None"]').val('');

	// We like numbers in our RSVP field
	if ($('#id_rsvpLimit').val().trim() == '') {
		$('#id_rsvpLimit').val('0');
	}

	// To restore the map we just ask if we have a lat and lon?
	if ($('#id_lat').val().trim() != '' && $('#id_lon').val().trim() != '') {
		// Then let's restore the state of the map
		restoreLocationState(
			Number($('#id_lat').val().trim()),
			Number($('#id_lon').val().trim()),
			[
				[Number($('#id_north').val()), Number($('#id_west').val())],
				[Number($('#id_south').val()), Number($('#id_east').val())]
			]
		);
	} else {
		// It's a new map! We like London, so how about we show that
		map.fitBounds(
			[
				[51.47860327187397,-0.16805648803710938],
				[51.5177162373547,-0.0926971435546875]
			]
		);
	}

	// If we have the when info
	if ($('#id_when').val().trim() != '') {
		// Then we can prime our interface by setting the start date from
		// the when info
		tStartDate = new Date($('#id_when').val());

		// And update the fields for the start info
		$('#id_from_date').val(getIsoStringFromDate(tStartDate));
		$('#id_from_time').val(getTimeStringFromDate(tStartDate));

		// And if we also have the duration
		if ($('#id_duration').val().trim() != '') {
			// Then we can figure our the time in milliseconds after the
			// start that the event will end
			duration = Number($('#id_duration').val().trim()) * 60000;

			// And create a date object representing that end point in time
			tEndDate = new Date(tStartDate.valueOf() + duration);

			// And update the fields for the end info
			$('#id_to_date').val(getIsoStringFromDate(tEndDate));
			$('#id_to_time').val(getTimeStringFromDate(tEndDate));
		}
	}


	// It is a good idea to not let the user plan an event in the past
	var d = new Date();
	$('#id_from_date').datepicker('setStartDate', d);
	$('#id_to_date').datepicker('setStartDate', d);

	// And if we have primed our interface
	if ($('#id_from_date').val().trim() != "" && $('#id_from_date').val().trim().match(dateReg)) {

		// Then we can set our global var with the start date
		setStartDate(getDateFromIsoString($('#id_from_date').val()));

		// And prevent the user from selecting an end date prior to the start date
		$('#id_to_date').datepicker('setStartDate', $('#id_from_date').val());

		// And if we have an end date
		if ($('#id_to_date').val().trim() != "" && $('#id_to_date').val().trim().match(dateReg)) {

			// Then we can set our global var with the end date
			setEndDate(getDateFromIsoString($('#id_to_date').val()));
		} else {

			// Or default the end date to the same as the start date
			$('#id_to_date').val($('#id_from_date').val());
		}
	} else {
		// But if we don't have a primed form, then it's a blank form and we
		// should do something useful, like putting in tomorrow's date
		d.setDate(d.getDate() + 1);
		var s = getIsoStringFromDate(d);

		$('#id_from_date').val(s);
		$('#id_to_date').val(s);
		
		// Remember to update the global vars whenever we manually touch the
		// form values
		setStartDate(d);
		setEndDate(d);
	}

	// Need to determine whether we have a fromTime, and if we do we can
	// set the form to that, otherwise we will use 'current', which literally
	// means whatever the user's clock is
	var fromTime = ($('#id_from_time').val().trim() != "") ?
		$('#id_from_time').val() :
		'current';

	$('#id_from_time')
		// Create the time picker and set the time
		.timepicker({"disableFocus": true, "defaultTime": fromTime})
		// When a user goes into the field show the picker
		.on('focus', function() {
			$('#id_from_time').timepicker('showWidget');
		})
		// And if they change the value, update the form state
		.on('change', function() {
			validateDateTimes();

			// validateDateTime sets the duration, and it could be negative!
			// If it is negative then the end time should move forward so that
			// it is not negative
			if (duration < 0) {
				$('#id_to_time').val($('#id_from_time').val());
			}
		});

	// As above, use the form or use the clock
	var toTime = ($('#id_to_time').val().trim() != "") ?
		$('#id_to_time').val() :
		'current';

	$('#id_to_time')
		// Create the time picker and set the time
		.timepicker({"disableFocus": true, "defaultTime": toTime})
		// Show the picker when the user enters the field
		.on('focus', function() {
			$('#id_to_time').timepicker('showWidget');
		})
		// If the value changes, update the form state
		.on('change', function() {
			validateDateTimes();

			// And if the duration is negative, bump the time backwards
			if (duration < 0) {
				$('#id_from_time').val($('#id_to_time').val());
			}
		});

	// And as we've jigged all of the dates and times around, update the
	// form state
	validateDateTimes();
}

function isEmpty(e) {
	return (e.val().trim() == '');
}
function checkEmpty(e) {
	if (isEmpty($(e))) {
		addError($(e))
	} else {
		removeError($(e))
	}
}
function addError(e) {
	e.parent().addClass('has-error')
}
function removeError(e) {
	e.parent().removeClass('has-error')
}

$('#id_title').on('change', function() {
	checkEmpty(this);
}).on('blur', function() {
	checkEmpty(this);
});

// A last catch... on submit just double check those date fields
$('#eventForm').submit(function() {
	if (isEmpty($('#id_title'))) {
		addError($('#id_title'))
		return false;
	}
	return validateDateTimes();
});
