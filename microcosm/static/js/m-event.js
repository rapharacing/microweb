// Create map
var map = L.map('map')
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

// If this is the edit screen and we need to set the map to known values then
// we do so here
function restoreLocationState(lat, lng, bounds) {
	map.fitBounds(bounds);

	// Bounds will always be 1 level too far out due to imprecision in the
	// numbers and Leaflet aggressively ensuring the bounds fit inside the
	// map area. To prevent us slowly zooming out, we zoom in
	map.zoomIn();

	var marker = L.marker(new L.LatLng(lat, lng));
	map.addLayer(marker);
}

function formatDate(d) {
	var monthsShort = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

	var hh = d.getHours();
	var pm = (hh > 12);

	return d.getDate() + ' ' +
		monthsShort[d.getMonth()] + ' ' + 
		d.getFullYear() + ', ' +
		(hh > 12 ? hh - 12: hh) + ':' +
		d.getMinutes() + ' ' +
		(pm ? 'p.m.' : 'a.m.');
}

function getDateFromIsoString(input) {
	var parts = input.match(/(\d+)/g);
	// new Date(year, month [, date [, hours[, minutes[, seconds[, ms]]]]])
	return new Date(parts[0], parts[1]-1, parts[2], parts[3], parts[4]); // months are 0-based
}

function showEndDate(startDate, duration) {
	// We need a date object
	var sd = getDateFromIsoString(startDate);
	if (sd) {
		// And the duration in minutes
		dur = Number(duration);
		if (dur) {
			// To figure out the millisecond difference
			dur = dur * 60000;
			// And create a date object representing that end point in time
			var ed = new Date(sd.valueOf() + dur);
			// And update the fields for the end info
			$('#ends').text(formatDate(ed));
		}
	}
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

$('#id_markdown').on('change', function() {
	checkEmpty(this);
}).on('blur', function() {
	checkEmpty(this);
});

$('#commentForm').submit(function() {
	if (isEmpty($('#id_markdown'))) {
		addError($('#id_markdown'))
		return false;
	}

	// Client-side dupe check
	md5 = hex_md5($('#id_markdown').val())
	if (this.md5 && this.md5 == md5) {
		return false
	}
	this.md5 = md5;

	return true;
});

$(document).ready(function() {
	$('#id_markdown').addClass('input-with-feedback').parent().addClass('control-group');
});
