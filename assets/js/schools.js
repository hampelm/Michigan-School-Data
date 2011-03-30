$(function() {
	$( "#tabs" ).tabs();


    $.widget( "custom.complete_custom", $.ui.autocomplete, {
		_renderMenu: function( ul, items ) {
			var self = this;
			var too_long = false;
			if (items.length > 10){
			    original_length = items.length;
    			too_long = true;
    			items = items.slice(0,10);
			}
			$.each( items, function( index, item ) {
				ul.append( "<li class='ui-autocomplete-category'><a href='/building/" + item.buildingcode + "'>" + item.buildingname + "</a></li>" );
			});
			if(too_long) {
			    ul.append( "<li class='ui-autocomplete-category see-all'><a href='/search/" + 'term' + "'><strong>See all " + original_length + " results</strong></a></li>" )
			} 
		}
	});

	$( "#search" ).complete_custom({
        source: "/search/json",
        select: function( event, ui ) {
          window.location.href = ui.item.href;
        },
        
		minLength: 2
	});
    
    $(".tooltip").hover(
        function(){
            var pos = $(this).offset();  
            var width = $(this).width();
            var tooltip_height = $(this).find(".tooltip-text").height();
            $(this).find(".tooltip-text").css( { "left": pos.left - 230 + "px", "top":pos.top - tooltip_height + "px" } );
            $(this).find(".tooltip-text").show();
        },
        function(){
            $(this).find(".tooltip-text").hide();
        }
    );
	
});


var geocoder;
var map;
function initialize() {
  geocoder = new google.maps.Geocoder();
  var latlng = new google.maps.LatLng(-34.397, 150.644);
  var myOptions = {
    zoom: 14,
    center: latlng,
    mapTypeId: google.maps.MapTypeId.ROADMAP,
    zoomControl: true,
    mapTypeControl: false,
    streetViewControl: false,
  }
  map = new google.maps.Map(document.getElementById("map_canvas"), myOptions);
  codeAddress();
}

function codeAddress() {
  var address = document.getElementById("geocode_address").innerHTML.trim();
  geocoder.geocode( { 'address': address}, function(results, status) {
    if (status == google.maps.GeocoderStatus.OK) {
      map.setCenter(results[0].geometry.location);
      var marker = new google.maps.Marker({
          map: map, 
          position: results[0].geometry.location
      });      
    } else {
        // Hide the map if geocode was unsuccessful
        document.getElementById('map_canvas').style.display = 'none';    
    }
  });
}


