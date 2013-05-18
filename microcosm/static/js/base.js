function updateTimes() {
	$('time').each(function(i) {
		var t = $(this);
		var dt = t.attr('datetime');
		if (dt && dt.trim() != '') {
			var m = moment(dt);
			var f = t.attr('format');
			// Relative date for simplicity
			var td = (f && f.trim() != '') ? m.format(f) : m.fromNow();
			if (t.text() != td) {
				t.text(td);
			}
			// Tooltip for precise date
			var tt = t.attr('title');
			var tip = m.format('LLLL');
			if (!tt || tt != tip) {
				t.attr('title', tip);
			}
		}
	});
}
if (jQuery && moment) {
	updateTimes();
}

$('document').ready(function() {
	updateTimes();
	setInterval(updateTimes, 60000); // Update every minute
});
