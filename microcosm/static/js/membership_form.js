function Role (opts, criterion) {
	// criteria container element
	this.list_criteria = '.criteria-list';
	if (typeof opts.criteria !== 'undefined') {
		if (typeof opts.criteria == 'string') {
			this.list_criteria  = opts.criteria;
			this.$list_criteria = $(this.list_criteria);
		} else {
			this.list_criteria = $opts.criteria[0];
			this.$list_criteria = $(this.list_criteria);
		}
	}

	// individuals container element
	this.list_members = '.list-participants';
	if (typeof opts.individuals !== 'undefined') {
		if (typeof opts.individuals == 'string') {
			this.list_members  = opts.individuals;
			this.$list_members = $(this.individuals);
		} else {
			this.list_members = $opts.individuals[0];
			this.$list_members = $(this.list_members);
		}
	}

	// maps cordinates to <input>s
	this.mappings = {
		'name'         : {el: 'input[name=name]',                 value: "" },
		'members'      : {el: 'input[name=invite]',               value: "" },
		'includeUsers' : {el: 'input[name=include_registered]',   value: "0" },
		'includeGuests': {el: 'input[name=include_unregistered]', value: "0" },
		'isModerator'  : {el: 'input[name=is_moderator]',         value: "0" },
		'isBanned'     : {el: 'input[name=is_banned]',            value: "0" },
		'canRead'      : {el: 'input[name=can_read]',             value: "0" },
		'canCreate'    : {el: 'input[name=can_create]',           value: "0" },
		'canEdit'      : {el: 'input[name=can_edit_others]',      value: "0" },
		'canDelete'    : {el: 'input[name=can_delete_others]',    value: "0" }
	};

	if (typeof opts.mappings !== 'undefined') {
		this.mappings = $.extend({}, this.mappings, opts.mappings);
	}

	this.criteria = (criterion) ? criterion : [];
}

// Takes internal state and makes sure the form reflects it
Role.prototype.updateForm = function(){
	var input;
	for(var i in this.mappings){
		if (typeof this.mappings[i].value !== 'undefined'){
			inputs = $(this.mappings[i].el);

			for (var ii = 0; ii < inputs.length; ii++) {
				input = $(inputs[ii]);

				if (inputs[ii].type == 'radio') {
					p = input.parent();
					if (inputs[ii].value == this.mappings[i].value) {
						inputs[ii].checked = true;
						if (!p.hasClass("active")) {
							p.addClass("active");
						}
					} else {
						if (p.hasClass("active")) {
							p.removeClass("active");
						}
					}
				} else {
					input.val(this.mappings[i].value);
				}
			}
		}
	}
	return this;
};

// Ensures that internal state is reflecting whatever the form currently says
Role.prototype.updateState = function(){
	var input;
	for(var i in this.mappings){
		if (typeof this.mappings[i].value !== 'undefined'){
			inputs = $(this.mappings[i].el);

			for (var ii = 0; ii < inputs.length; ii++) {
				if (inputs[ii].type == 'radio') {
					if (inputs[ii].checked == true) {
						this.mappings[i].value = inputs[ii].value;
					}
				} else {
					this.mappings[i].value = $(inputs[ii]).val();
				}
			}
		}
	}

	return this;
};

/////////////////////
// criteria widget //
/////////////////////
(function(w, d, $, undefined) {
	/*
	inline form for membership groups criteria
	-----------------------------------

	assumes the following markup:

	<div class="form-widget criteria-list">
		<div class="form-widget-empty-state">
			No criteria is set for this group.
			<a href="javascript:void 0">Add a criteria for users to join this group</a>
		</div>
		<div class="form-widget-list"></div>
		<div class="form-widget-inlineform"></div>
	</div>
	*/

	var ListWidget = (function() {

		var View = function(opts) {
			this.el = false;
			if (typeof opts.el !== "undefined") {
				this.el = opts.el;
			}

			this.data = [];
			if (typeof opts.data !== "undefined") {
				this.add(opts.data);
			}

			this.$el = $(this.el);

			this.$el.emptyState = this.$el.find('.form-widget-empty-state');
			this.$el.display    = this.$el.find('.form-widget-list');
			this.$el.form       = this.$el.find('.form-widget-inlineform');

			this.bind();
		};

		View.prototype.add = function(datasets) {
			if (typeof datasets === "object") {
				for (var dataset in datasets) {
					this.data.push( datasets[dataset] );
				}
			} else {
				throw "add(): expected [object] but got [" + typeof keys + "]";
			}
		};

		// renders list using this.data
		// template is hardcoded! (FIXME)
		View.prototype.render = function(){

			var fragment = $('<ul></ul>'),
					list_items = "";


			for (var i=0, j=this.data.length; i < j; i++) {

				list_items += '<li>';

				if (i !== 0) {
					if (this.data[i][0] === "and") {
						list_items += 'and ';
					} else {
						list_items += '<em>or</em></li><li>';
					}
				}

				var predicate = '';
				switch (this.data[i][2]) {
					case 'gt': predicate = "is greater than"; break;
					case 'ge': predicate = "is greater than or equal to"; break;
					case 'eq': predicate = "equals"; break;
					case 'le': predicate = "is less than or equal to"; break;
					case 'lt': predicate = "is less than"; break;
					case 'neq': predicate = "is not equal to"; break;
					case 'substr': predicate = "contains"; break;
					case 'nsubstr': predicate = "does not contain"; break;
				}

				list_items +=
					'<span class="text-warning remove align-right" data-index="' + i + '">Remove</span>' +
					'<strong>' + this.data[i][1] + '</strong> ' +
					predicate + ' ' +
					'<strong>' + this.data[i][3] + '</strong>';

				list_items += '</li>';
			}

			if (this.data.length < 1) {
				this.$el.emptyState.show();
				this.$el.display.hide();
			} else {
				this.$el.emptyState.hide();
				this.$el.display.show();
				fragment.append("<lh>Members join this group if:</lh>")
					.append(list_items)
					.append('<a class="form-list-form-toggle">Add criteria</a>');
			}

			this.$el.display.html(fragment);
		};

		// debug function
		View.prototype.log = function() {
			console.log('el: ', this.el);
			console.log('data: ', this.data);
		};

		// removes items from this.data
		View.prototype.remove = function(e) {
			var li = $(e.currentTarget), index = li.attr('data-index');

			if (typeof this.data[index] !== "undefined") {
				this.data.splice(index,1);
				this.render();
			}
		};

		// unbinds widget from dom
		View.prototype.destroy = function(){
			this.$el.display.html("").off();
			this.$el.display = null;

			this.$el.form.off();
			this.$el.form = null;

			this.$el.off();
		};

		// form events

		/**
		*   submit
		*   scrapes form elements inside this.$el.form, saves values into an array,
		*   adds to this.data and re-renders the list
		*/
		View.prototype.submit = function() {

			var valueField = $('input[name=value]');
			if ($.trim(valueField.val()) == '') {
				alert('A value must be specified');
				valueField.focus();
				return;
			} else {
				if ($('select[name=condition] option:checked').val() == 'created') {
					if (valueField.val().length != 10 || isNaN(parseIsoDate(valueField.val()))) {
						alert('A date value in ISO format 2014-02-14 must be specified');
						valueField.focus();
						return;
					}
				} 
			}

			var fields_values = [];

			// assumes:-
			// 1. we know nothing of the form
			// 2. <input>s and <select>s with "name" attribute are valid fields
			var fields = this.$el.form.find('input[name], select[name]');

			fields_values = $.map(fields,function(field,index) {
				if (field.tagName === "INPUT") {
					if (field.type == 'radio') {
						if (field.checked) {
							return field.value;
						}
					} else {
						return field.value;
					}
				} else if (field.tagName === "SELECT") {
					return field.value;
				} else {
					// pass
				}
			});

			this.add([fields_values]);

			// re-render the list
			this.render();
		};

		View.prototype.toggleForm = function(){
			this.$el.form.toggle();
		};

		// bind events
		View.prototype.bind = function(){
			this.$el.emptyState.on('click',$.proxy(function() {
				this.toggleForm();
			}, this));

			// only binds for elements inside this.$el.display
			var display_events = [
				['click', '.remove', 'remove'],
				['click', '.form-list-form-toggle', 'toggleForm']
			];

			for (var i in display_events) {
				this.$el.display.on(display_events[i][0], display_events[i][1], $.proxy(this[display_events[i][2]], this));
			}

			// only binds for elements inside this.$el.form
			var form_events = [
				['click', '.submit', 'submit']
			];

			for (i in form_events) {
				this.$el.form.on(form_events[i][0], form_events[i][1], $.proxy(this[form_events[i][2]], this));
			}
		};

		return View;
	})();

	// initialize
	criteria = new ListWidget({
		el : '.criteria-list'
	});

	criteria.render();

})(window,document,jQuery,undefined);


// Events for the criteria form to ensure validation
function validateCondition() {
	var condition = 'select[name=condition]';
	var predicate = 'select[name=predicate]';
	var predicates = $(predicate + ' option');

	var condition_selected = $(condition + ' option:selected');
	if (condition_selected.length != 1) {
		$(condition + ' option:first').prop('selected', true);
		return;
	}

	condition_selected = condition_selected[0];

	switch (condition_selected.value) {
		case "commentCount":
			restrictPredicates('number');
			$('input[name=value]').attr('placeholder','1000').val('');
			break;
		case "created":
			restrictPredicates('date');
			$('input[name=value]').attr('placeholder','2014-02-14').val('');
			break;
		case "profileName":
			restrictPredicates('string');
			$('input[name=value]').attr('placeholder','John Smith').val('');
			break;
		default:
			var kv = prompt('Please enter the profile attribute name', 'is_member');
			if (kv) {
				$(condition_selected).text(kv).val(kv);
				restrictPredicates('all');
				$('input[name=value]').attr('placeholder','Value').val('');
			}
	}

} // function validateCondition()

function validateValue() {

	var conds = $('select[name=condition] option:checked');
	if (conds.length != 1) {
		return
	}

	var valueField = $('input[name=value]');
	switch ($(conds[0]).val()) {
		case "commentCount":
			// Int
			if (isNaN(Number(valueField.val())) || isNaN(parseInt(valueField.val()))) {
				valueField.val('');
			} else {
				// Get rid of decimals, etc
				valueField.val(parseInt(valueField.val()));
			}
			break;
		case "created":
			// Date
			// This handles YYYY-MM-DD as it's being typed by making each char optional
			if (!/^(\d(\d(\d(\d(\-(\d(\d(\-(\d(\d)?)?)?)?)?)?)?)?)?)$/.test(valueField.val())) {
				valueField.val('');
			}
			break;
		case "profileName":
			// String, we don't care... it can be anything but we'd like it trimmed
			valueField.val($.trim(valueField.val()));
			break;
		default:
			restrictPredicates(sniffDatatype($('input[name=value]').val()));
	}
}

function parseIsoDate(s){
    var day, tz, 
    rx = /^(\d{4}\-\d\d\-\d\d)$/, 
    p = rx.exec(s) || [];
    if (p[1]){
        day = p[1].split(/\D/).map(function(itm){
            return parseInt(itm, 10) || 0;
        });
        day[1] -= 1;
        day = new Date(Date.UTC.apply(Date, day));
        if (!day.getDate()) return NaN;
        if (p[5]){
            tz= parseInt(p[5], 10)*60;
            if (p[6]) tz += parseInt(p[6], 10);
            if (p[4] == "+") tz*= -1;
            if (tz) day.setUTCMinutes(day.getUTCMinutes()+ tz);
        }
        return day;
    }
    return NaN;
}

function sniffDatatype(val) {
	if (val == '') {
		return 'all';
	}

	if (val == 'true' || val == 'false') {
		return 'bool';
	}

	if (!isNaN(Number(val))) {
		return 'number';
	}

	if (val.length == 10 && !isNaN(parseIsoDate(val))) {
		return 'date';
	}

	return 'string';
}

function restrictPredicates(datatype) {
	var predicate = 'select[name=predicate]';
	if ($(predicate).attr('datatype') == datatype) {
		return;
	}
	$(predicate).attr('datatype', datatype);

	var predicates = $(predicate + ' option');
	$.each(predicates, function(i, v) {
		switch (datatype) {
			case 'all':
				$(v).prop('disabled', false);
				if (i == 0) {
					$(v).prop('selected', true);
				}
				break;
			case 'number':
				switch (v.value) {
					case "gt":
						$(v).prop('disabled', false).prop('selected', true);
						break;
					case "ge":
					case "le":
					case "lt":
					case "eq":
					case "neq":
						$(v).prop('disabled', false);
						break;
					case "substr":
					case "nsubstr":
						$(v).prop('disabled', true);
						break;
				}
				break;
			case 'date':
				switch (v.value) {
					case "le":
						$(v).prop('disabled', false).prop('selected', true);
						break;
					case "gt":
					case "ge":
					case "lt":
					case "eq":
					case "neq":
						$(v).prop('disabled', false);
						break;
					case "substr":
					case "nsubstr":
						$(v).prop('disabled', true);
						break;
				}
				break;
			case 'bool':
				switch (v.value) {
					case "eq":
						$(v).prop('disabled', false).prop('selected', true);
						break;
					case "neq":
						$(v).prop('disabled', false);
						break;
					case "gt":
					case "ge":
					case "le":
					case "lt":
					case "substr":
					case "nsubstr":
						$(v).prop('disabled', true);
						break;
				}
				break;
			case 'string':
				switch (v.value) {
					case "eq":
						$(v).prop('disabled', false).prop('selected', true);
						break;
					case "neq":
					case "substr":
					case "nsubstr":
						$(v).prop('disabled', false);
						break;
					case "gt":
					case "ge":
					case "le":
					case "lt":
						$(v).prop('disabled', true);
						break;
				}
				break;
			default:
				$(v).prop('disabled', true);
		}
	});
}

$(document).ready(function() {
	validateCondition();
	$('select[name=condition]').bind("change", validateCondition);
	$('input[name=value]').bind("keyup", validateValue);
});



/////////////////////
//  people widget  //
/////////////////////
(function() {
	'use strict';

	(function() {
		'use strict'

		var subdomain = $('meta[name="subdomain"]').attr('content');

		var participating = new Participating({
			el         : '.list-participants',
			className  : 'list-people list-people-sm',
			static_url : subdomain
		});

		var peopleWidget = new PeopleWidget({
			el         : '#invite',
			is_textbox : true,
			static_url : subdomain,
			dataSource : subdomain + '/api/v1/profiles?disableBoiler&top=true&q='
		});

		// update the hidden input box
		var invite_input_field = $('input[name="invite"]');
		var updateInvitedField = function(){
			invite_input_field.val(peopleWidget.invitedListToDelimitedString());
		};

		// triggers when user clicks on a person in the autocomplete dropdown
		peopleWidget.onSelection(function(invited){
			if (invited.length > 0){
				participating.render(invited).show();
			}else{
				participating.hide();
			}
			peopleWidget.show();
			updateInvitedField();
		});

		// triggers when the user clicks on a person in the participants list
		participating.$el.on('click', 'li', function(e){
			var id = e.currentTarget.rel;
			peopleWidget.removePersonFromInvitedById(id).render();
			if (peopleWidget.people_invited.length>0) {
				participating.render(peopleWidget.people_invited).show();
			}else{
				participating.hide();
			}
			updateInvitedField();
		});
	})();
})();




$(document).ready(function() {
	$('#createForm').on("submit", function(e) {

		role.updateState();

		if ($.trim(role.mappings.name.value) == '') {
			alert('The membership group must have a name');
			$('input[name=name]').focus();
			return false;
		}

		data = {};

		// Core role info
		data.role = {
			"title": role.mappings.name.value,
			"includeGuests": (role.mappings.includeGuests.value == "1"),
			"includeUsers": (role.mappings.includeUsers.value == "1"),
			"moderator": (role.mappings.isModerator.value == "1"),
			"banned": (role.mappings.isBanned.value == "1"),
			"read": (role.mappings.canRead.value == "1"),
			"create": (role.mappings.canCreate.value == "1"),
			"update": (role.mappings.canEdit.value == "1"),
			"delete": (role.mappings.canDelete.value == "1"),
			"closeOwn": (role.mappings.canDelete.value == "1"),
			"openOwn": (role.mappings.canDelete.value == "1"),
			"readOthers": (role.mappings.canRead.value == "1")
		}

		// Profiles
		data.profiles = [];

		$('div.list-participants ul li a:visible').each(function(i, v) {
			data.profiles[data.profiles.length] = v.id;
		});

		// Criteria
		data.criteria = [];
		
		var crits = [];
		var orGroup = 0;
		for (var ii = 0; ii < criteria.data.length; ii++) {

			var c = criteria.data[ii];
			if (c[0] == "or") {
				orGroup++;
			}

			var crit = {
				orGroup: orGroup,
			}

			switch (c[1]) {
				case "commentCount":
				case "created":
				case "profileName":
					crit.profileColumn = c[1];
					break;
				default:
					crit.attrKey = c[1];
			}

			crit.predicate = c[2];

			switch (sniffDatatype(c[3])) {
				case "all":
					alert('One of the criteria has a blank value');
					return false;
					break;
				case "number":
					crit.value = Number(c[3]);
					break;
				case "bool":
					crit.value = (c[3] == "true");
					break;
				case "date":
				case "string":
					crit.value = c[3];
					break;
			}

			data.criteria[data.criteria.length] = crit 
		}

		function getCookie(name) {
			var cookieValue = null;
			if (document.cookie && document.cookie != '') {
				var cookies = document.cookie.split(';');
				for (var i = 0; i < cookies.length; i++) {
					var cookie = jQuery.trim(cookies[i]);
					// Does this cookie string begin with the name we want?
					if (cookie.substring(0, name.length + 1) == (name + '=')) {
						cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
						break;
					}
				}
			}
			return cookieValue;
		}
		var csrftoken = getCookie('csrftoken');

		$.ajaxSetup({
			beforeSend: function(xhr, settings) {
				xhr.setRequestHeader("X-CSRFToken", csrftoken);
			}
		});

		console.log(data);
		$.ajax({
			type: 'POST',
			url: '../api/',
			contentType: 'application/json; charset=UTF-8',
			processData: false,
			data: JSON.stringify(data),
			dataType: 'json',
			success: function(data) {
				console.log(data);
				alert(true);
			},
		});

		return false;
	});
});
