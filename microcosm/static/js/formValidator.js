(function(){

  // usage
  //
  // var a = new Validator( <html#form>, {
  //   rules : { '<form#field.name>' : 'test_name' },
  //   tests : { 'test_name' : <js#function($jquery#field)> }
  // });
  // 2 builtin tests called 'not_empty' and 'not_duplicate'
  // tests should return false if invalid
  //
  // eg.
  // var validateObject = new Validator(
  //   document.getElementById('myform'),
  //   {
  //     rules : {
  //       'first_name' : 'not_empty',
  //       'last_name'  : ['not_empty', 'minLength3' ]
  //     },
  //     tests : {
  //       'minLength3' : function(field){ return field.val().length > 3; }
  //     }
  //   });
  //
  // on failure, preventsDefault() the form, returns array of errors

  var Validator = (function(){

    var validator = function(form, options){

      this.form   = form;
      this.$form  = $(this.form);

      this.errors = [];
      this.initialState = this.getSerializedForm();

      // tests
      this.tests = {
        'not_empty'     : this.not_empty
      };
      if (typeof options.tests !== 'undefined'){
        this.tests = $.extend({},this.tests,options.tests);
      }

      // rules
      var user_rules = {};
      if (typeof options.rules !== 'undefined'){
        user_rules = options.rules;
      }
      this.rules = $.extend({},user_rules);


      this.$form.on('submit', $.proxy(this.validate,this));

      return this;
    };

    // tests
    validator.prototype.not_empty = function(field){
      return field.val().trim() !== '';
    };

    validator.prototype.getSerializedForm = function(){

      var serializedArray = this.$form.serializeArray();
      serializedArray.shift();// remove the csrf token

      var serializedArrayToString = [];
      for(var i=0,j=serializedArray.length;i<j;i++){
        serializedArrayToString.push( serializedArray[i].name + '=' + serializedArray[i].value );
      }
      return $.trim(serializedArrayToString.join('&'));
    };

    validator.prototype.not_duplicate = function(value){
      return this.getSerializedForm() === this.initialState;
    };


    validator.prototype.validate = function(e){

      this.errors = [];

      // dupe check
      if (this.not_duplicate()){
        this.errors.push('dupe');
      }

      var field;
      for(var field_name in this.rules){
        field = this.$form.find('[name='+field_name+']');

        if (typeof this.rules[field_name] !== 'undefined'){

          if (typeof this.rules[field_name] == 'object'){ // is array

            for(var i=0,j=this.rules[field_name].length;i<j;i++){
              if( !this.tests[this.rules[field_name][i]](field) ){
                this.errors.push([field_name, this.rules[field_name][i]].join(":"));
              }
            }

          }else{ // not an array
            if( !this.tests[this.rules[field_name]](field) ){
              this.errors.push([field_name, this.rules[field_name]].join(":"));
            }
          }
        }

      }

      if (this.errors.length>0){
        e.preventDefault();
        console.log(this.errors);
        return this.errors;
      }
    };

    return validator;

  })();

  window.Validator = Validator;
})();