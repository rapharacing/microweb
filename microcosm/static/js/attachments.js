(function(w,d,$,undefined){

  var FileHandler = (function(){

    var fileHandler = function(opts){

      if (typeof opts.el !== 'undefined'){
        if (typeof opts.el === 'string'){
          this.el_name  = opts.el;
          this.$el      = $(this.el);
          this.el       = this.$el[0];
        }else if (typeof opts.el === 'object'){

          this.el      = opts.el;
          this.$el     = $(opts.el);
          this.el_name = '.'+this.el.className;

        }else{
          return false;
        }
      }

      if (typeof opts.dropzone !== 'undefined'){
        this.dropzone = opts.dropzone;
      }
      this.input = this.$el.find('input[type=file]')[0];

      this.stack = [];
      this.bind();

      return this;
    };

    fileHandler.prototype.removeFile = function(index){
      this.stack.splice(index,1);
      this.input.files = this.stack;

      if(typeof this.onRemove !== 'undefined' && typeof this.onRemove === 'function'){
        this.onRemove(this.stack);
      }
    };

    fileHandler.prototype.clear = function(){
      for(var i=0,j=this.stack.length;i<j;i++){
        this.stack.pop();
      }
    };

    fileHandler.prototype.parse = function(files){

      var file, reader, callback;

      if (files.length < 1){
        return;
      }

      this.input.files = files;
      this.callback_counter = this.input.files.length;

      callback = $.proxy(function(e,i){
        this.stack.push($.extend({},this.input.files[i],{data:e.target.result}));

        this.callback_counter--;
        if (this.callback_counter <= 0){
          if(typeof this.onDragged !== 'undefined' && typeof this.onDragged === 'function'){
            this.onDragged(this.stack);
          }
        }
      },this);

      for(var i=0,j=files.length;i<j;i++){
        if (files[i].type.match('image.*')){

          reader = new FileReader();
          reader.onload = (function(i){
            return function(e){
              callback(e,i);
            };
          })(i);

          reader.readAsDataURL(files[i]);
        }
      }

      return this;

    };

    fileHandler.prototype.onDragged = function(fn){
      if(typeof fn === 'function'){
        this.onDragged = fn;
      }
      return this;
    };

    fileHandler.prototype.onRemove = function(fn){
      if(typeof fn === 'function'){
        this.onRemove = fn;
      }
      return this;
    };

    fileHandler.prototype.changeHandler = function(e){
      //this.parse(e.target.files);
    };

    fileHandler.prototype.dragHandler = function(e){
      e.stopPropagation();
      e.preventDefault();
    };

    fileHandler.prototype.dropHandler = function(e){
      e.stopPropagation();
      e.preventDefault();
      this.parse(e.originalEvent.dataTransfer.files);
    };

    fileHandler.prototype.bind = function(){

      var events = [
        ['change',    'input[type=file]', 'changeHandler'],
        ['drop',      this.dropzone,      'dropHandler'],
        ['dragover',  this.dropzone,      'dragHandler']
      ];

      for(var i in events){
        this.$el.on(events[i][0], events[i][1], $.proxy(this[events[i][2]], this) );
      }
    };

    return fileHandler;

  })();

  window.FileHandler = FileHandler;

})(window, document, jQuery);