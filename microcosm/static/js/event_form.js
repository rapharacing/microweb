/**
*   event date and time controls
*/
(function(){
  'use strict';

  var EVENT_DATE_TYPE_TBA      = 0,
      EVENT_DATE_TYPE_SINGLE   = 1,
      EVENT_DATE_TYPE_MULTIPLE = 2;

  // flag used to toggle calendar elements
  var event_date_type = EVENT_DATE_TYPE_SINGLE;

  // cache references to the calendar elements we are interested in
  var elements_event_calendars         = $('.form-datepicker'),
      elements_event_date_type_single  = $('.form-datepicker-single'),
      elements_event_date_type_mutiple = $('.form-datepicker-multiple');

  // cache references to the event date type radio buttons ("single", "multiple", "tba")
  var event_date_type_options = $('#event-date-type-options input[name="date-type"]');

  // when user clicks an event date type radio button,
  // set event_date_type with the radio button value and toggle the calendar elements
  event_date_type_options.on('change',function(e){
    var selected = event_date_type_options.filter(':checked');
    event_date_type = selected.val();
    toggleCalendars();
  });

  // if..else based on event_date_type
  // _____________   _____________
  // |      x     |  |      z     |
  // |____________|  |____________|
  //
  // [ x ] to [ y ]  [ z ]

  function toggleCalendars(){
    // shows all "x,y", hides all "z"
    if (event_date_type == EVENT_DATE_TYPE_SINGLE){
      elements_event_calendars.show();
      elements_event_date_type_single.show();
      elements_event_date_type_mutiple.hide();
    }
    // shows all "x,z", hides all "y"
    if (event_date_type == EVENT_DATE_TYPE_MULTIPLE){
      elements_event_calendars.show();
      elements_event_date_type_single.hide();
      elements_event_date_type_mutiple.show();
    }
    // hides "x,y,z"
    if (event_date_type == EVENT_DATE_TYPE_TBA){
      elements_event_calendars.hide();
    }
  }

  // template object for calendar display
  // @param  dateObject - a javascript Date object
  // @return string     - string which will be converted and injected into the dom
  var template = function(dateObject){

    var d = dateObject,
        locale_days   = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
        locale_months = [
          "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"
        ],
        output = "";

    output = '<div class="item-event-date">' +
               '<span class="item-event-date-digit">' + d.getDate() + '</span>' +
               '<span class="item-event-date-day">' + locale_days[d.getDay()] +
                 '<strong>'+ locale_months[d.getMonth()] + ' ' + d.getFullYear() + '</strong>' +
               '</span>' +
             '</div>';

    return output;
  };

  // updates event dates for post request
  // @param ev   - expects a specific event object returned by bootstrap-datepicker plugin
  //             - at a minimum { currentTarget: <domelement>, date: <jsDateObject> }
  function updateEventDates(ev){
    updateDatePickerUI(ev);
  }

  // handles the UI of the calendar
  // @param ev   - expects a specific event object returned by bootstrap-datepicker plugin
  //             - at a minimum { currentTarget: <domelement>, date: <jsDateObject> }
  function updateDatePickerUI(ev){
    var parent = $(ev.currentTarget);
    parent.datepicker('hide');
    parent.html(template(ev.date));
  }

  // init: bootstrap-calendar widget
  var event_start_date = $('#event-start-calendar .event-start-calendar-contents').datepicker()
                         .on('changeDate', updateEventDates);

  var event_end_date   = $('#event-end-calendar .event-start-calendar-contents').datepicker()
                         .on('changeDate', updateEventDates);


  // init: toggle calendars on page load
  toggleCalendars();

  // init: populate the calendars on page load
  var today    = new Date();
  var tomorrow = new Date();
  tomorrow.setDate(today.getDate()+1);

  event_start_date.html( template( today ) );
  event_end_date.html( template( tomorrow ) );

})();

/*
*  toggle location form
*/
(function(){

  var LOCATION_TYPE_AVAILABLE = 1,
      LOCATION_TYPE_TBA       = 0,
      location_type_options   = $('#location-options input[name=location-type]'),
      form_location           = $('.form-location');

  location_type = LOCATION_TYPE_AVAILABLE;

  function toggleLocation(){
    if (location_type === LOCATION_TYPE_AVAILABLE){
      form_location.show();
    }
    if (location_type === LOCATION_TYPE_TBA){
      form_location.hide();
    }
  }

  location_type_options.on('change',function(e){
    var _this = $(e.currentTarget);
    location_type = parseInt(_this.val(),10);
    toggleLocation();
  });

})();


/*
*   form
*   attendee limit toggle
*/
(function(){
  'use strict';

  var attendee_limit_options = $('.attendee-options input[name=attendee-limit-option]'),
      attendee_limit_value   = $('.attendee-options input[name=attendee-limit-value]'),
      has_attendees_limit = false;

  // toggles the able/disable of the attendee limit input box
  function toggleAttendeeLimit(){

    if (has_attendees_limit){
      attendee_limit_value.attr('disabled',false);
      attendee_limit_value.focus();
    }else{
      attendee_limit_value.attr('disabled',true);
    }
  }

  // bind change event to radio buttons
  attendee_limit_options.on('change',function(e){
    var _this = $(e.currentTarget);
    has_attendees_limit = parseInt(_this.val(),10) === 1 ? true : false;
    toggleAttendeeLimit();
  });


})();
