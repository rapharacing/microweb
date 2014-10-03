/////////
// MAP //
/////////
(function(){

  var EventMap = (function(){
    var eventMap = function(options){
      // reference to map marker
      this.marker = [];

      var mapID = 'map-canvas';
      if (typeof options.map !== 'undefined'){
        mapID = options.map;
      }

      this.map = L.map( options.map , { zoomAnimation : false })
                  .setMaxBounds([[-90,-180],[90,180]]); // Restrict map to valid lat:lng pairs

      var googleLayer = new L.Google('ROADMAP');
      this.map.addLayer(googleLayer);

      //var cloudmadeLayer = new L.TileLayer("https://d1qte70nkdppk5.cloudfront.net/d6f1a0c60e9746faa7cbfaec4b92dff3/96931/256/{z}/{x}/{y}.png");
      var osmLayer = new L.TileLayer("http://otile1.mqcdn.com/tiles/1.0.0/map/{z}/{x}/{y}.jpg");

      this.map.addControl(new L.Control.Layers({
        'Open Street Map' : osmLayer,
        'Google Maps'     : googleLayer
        })
      );

      return this;
    };

    eventMap.prototype.addMarker = function(latlng){
      var newMarker = L.marker(latlng);
      this.marker.push(newMarker);
      return this;
    };

    eventMap.prototype.renderMarkers = function(){
      if (this.marker.length > 0){
        for(var i=0,j=this.marker.length;i<j;i++){
          this.map.addLayer( this.marker[i] );
        }
      }
      return this;
    };

    // If this is the edit screen and we need to set the map to known values then
    // we do so here
    // @param lat number
    // @param lng number
    // @param bounds array(array(north, west),array(south, east))
    eventMap.prototype.restore = function(lat, lng, bounds){

      this.map.fitBounds(bounds);
      // Bounds will always be 1 level too far out due to imprecision in the
      // numbers and Leaflet aggressively ensuring the bounds fit inside the
      // map area. To prevent us slowly zooming out with each edit, we zoom in
      this.map.zoomIn();

      this.addMarker(new L.LatLng(lat, lng));
      this.renderMarkers();
    };

    return eventMap;

  })();

  window.EventMap = EventMap;

  ////////////////
  // LOCAL TIME //
  ////////////////

  // A simple case of pulling the UTC values in the page, and allowing the
  // JavaScript locale to dictate the values.

  var startTime = null;
  var endTime = null;
  
  $("time[itemprop='startDate']").each(function() {
    startTime = new Date($(this).attr('datetime'));
    var p = $(this).closest('.item-event-date');
    
    // Set the date to the current locale
    p.find('.item-event-date-digit').first().text(startTime.getDate());
    var days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    p.find('.item-event-date-day').first().html(days[startTime.getDay()] + '<strong>' + months[startTime.getMonth()] + ' ' + startTime.getFullYear() + '</strong>');

    // Set the time to the current locale
    var t = p.find("time[itemprop='duration']");
    var dur = t.attr('datetime').substring(1,t.attr('datetime').length-1);
    endTime = new Date(startTime.getTime() + dur * 60000);

    if(t.text().indexOf('-') != -1){
      // Show start and end time
      t.text(
        (startTime.getHours() > 12 ? startTime.getHours()-12 : startTime.getHours()) +
        ':' + (startTime.getMinutes() < 10 ? '0' : '') + startTime.getMinutes() +
        ' ' + (startTime.getHours() >= 12 ? 'PM' : 'AM') + 
        ' - ' + 
        (endTime.getHours() > 12 ? endTime.getHours()-12 : endTime.getHours()) +
        ':' + (endTime.getMinutes() < 10 ? '0' : '') + endTime.getMinutes() +
        ' ' + (endTime.getHours() >= 12 ? 'PM' : 'AM')
      );
    } else {
      // Only show start time
      t.text(
        (startTime.getHours() > 12 ? d.getHours()-12 : startTime.getHours()) +
        ':' + (startTime.getMinutes() < 10 ? '0' : '') + startTime.getMinutes() +
        ' ' + (startTime.getHours() >= 12 ? 'PM' : 'AM')
      );
    }
  });

  $("time[itemprop='endDate']").each(function() {
    var p = $(this).closest('.item-event-date');
    
    // Set the date to the current locale
    p.find('.item-event-date-digit').first().text(endTime.getDate());
    var days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    p.find('.item-event-date-day').first().html(days[endTime.getDay()] + '<strong>' + months[endTime.getMonth()] + ' ' + endTime.getFullYear() + '</strong>');

    // Set the time to the current locale
    p.find(".item-event-date-time").first().text(
      (endTime.getHours() > 12 ? endTime.getHours()-12 : endTime.getHours()) +
      ':' + (endTime.getMinutes() < 10 ? '0' : '') + endTime.getMinutes() +
      ' ' + (endTime.getHours() >= 12 ? 'PM' : 'AM')
    );
  });

})();