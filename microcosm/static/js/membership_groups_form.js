(function(w,d,$,undefined){

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

  var ListWidget = (function(){

    var View = function(opts){
      this.el = false;
      if (typeof opts.el !== "undefined"){
        this.el = opts.el;
      }

      this.data = [];
      if (typeof opts.data !== "undefined"){
        this.add(opts.data);
      }

      this.$el = $(this.el);

      this.$el.emptyState = this.$el.find('.form-widget-empty-state');
      this.$el.display = this.$el.find('.form-widget-list');
      this.$el.form    = this.$el.find('.form-widget-inlineform');

      this.bind();
    };


    View.prototype.add = function(datasets){

      if (typeof datasets === "object"){
        for(var dataset in datasets){
          this.data.push( datasets[dataset] );
        }
      }else{
        throw "add(): expected [object] but got [" + typeof keys + "]";
      }
    };

    // renders list using this.data
    // template is hardcoded! (FIXME)
    View.prototype.render = function(){

      var fragment = $('<ul></ul>'),
          list_items = "";


      for(var i=0,j=this.data.length;i<j;i++){
        if (i !== 0 && this.data[i][0] === "or"){
          list_items += '<li class="divider"><strong>Or if:</strong></li>';
        }
        list_items += '<li>'+
                      '<span class="glyphicon glyphicon-remove remove" data-index="' + i + '"></span>' +
                      '<span class="glyphicon glyphicon-ok list-bullet"></span>' +
                      'has <strong>' +
                      this.data[i][1] + '</strong> is ' +
                      this.data[i][2] + ' <strong>' +
                      this.data[i][3] + '</strong></li>';
      }

      if (this.data.length < 1){
        this.$el.emptyState.show();
        this.$el.display.hide();
      }else{
        this.$el.emptyState.hide();
        this.$el.display.show();
        fragment.append("<lh>Members join this group if the member:</lh>")
                .append(list_items)
                .append('<a class="form-list-form-toggle">Add criteria</a>');
      }


      this.$el.display.html(fragment);

    };

    // debug function
    View.prototype.log = function(){
      console.log('el: ', this.el);
      console.log('data: ', this.data);
    };


    // removes items from this.data
    View.prototype.remove = function(e){
      var li = $(e.currentTarget),
          index = li.attr('data-index');

      if (typeof this.data[index] !== "undefined"){
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
    View.prototype.submit = function(){

      var fields_values = [];

      // assumes:-
      // 1. we know nothing of the form
      // 2. <input>s and <select>s with "name" attribute are valid fields
      var fields = this.$el.form.find('input[name], select[name]');

      fields_values = $.map(fields,function(field,index){

        if (field.tagName === "INPUT"){
          if (field.type == 'radio'){
            if (field.checked){
              return field.value;
            }
          }else{
            return field.value;
          }
        }else if (field.tagName === "SELECT"){
          return field.value;
        }else{
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

      this.$el.emptyState.on('click',$.proxy(function(){
        this.toggleForm();
      },this));

      // only binds for elements inside this.$el.display
      var display_events = [
        ['click', '.remove', 'remove'],
        ['click', '.form-list-form-toggle', 'toggleForm']
      ];

      for(var i in display_events){
        this.$el.display.on(display_events[i][0], display_events[i][1], $.proxy(this[display_events[i][2]], this) );
      }


      // only binds for elements inside this.$el.form
      var form_events = [
        ['click', '.submit', 'submit']
      ];

      for(i in form_events){
        this.$el.form.on(form_events[i][0], form_events[i][1], $.proxy(this[form_events[i][2]], this) );
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