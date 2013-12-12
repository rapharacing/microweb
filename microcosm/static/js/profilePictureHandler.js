(function(w,d,$,undefined){

  var FileHandler = (function(){

    var fileHandler = function(opts){
      this.el = false;
      if (typeof opts.el !== 'undefined'){
        this.el    = document.querySelectorAll(opts.el);
        this.$el   = $(this.el);
        this.label = this.$el.find('label');
      }
      this.bind();
    };

    fileHandler.prototype.activateLabel = function(backgroundImage){
      this.label
        .addClass('active')
        .css('background-image', "url(" + backgroundImage + ")");
    };

    fileHandler.prototype.deactivateLabel = function(){
      this.label
        .removeClass('active')
        .css('background-image', "");
    };

    fileHandler.prototype.update = function(files){

      var file;

      if (files.length < 1){
        this.deactivateLabel();
        return;
      }

      file = files[0];

      if (!file.type.match('image.*')){
        this.deactivateLabel();
        return;
      }

      var reader = new FileReader();

      reader.onload = $.proxy(function(e){
        this.activateLabel(e.target.result);
      },this);

      reader.readAsDataURL(file);

    };

    fileHandler.prototype.changeHandler = function(e){
      this.update(e.target.files);
    };

    fileHandler.prototype.dragHandler = function(e){
      e.stopPropagation();
      e.preventDefault();
    };

    fileHandler.prototype.dropHandler = function(e){
      e.stopPropagation();
      e.preventDefault();
      this.update(e.originalEvent.dataTransfer.files);
    };

    fileHandler.prototype.bind = function(){

      var events = [
        ['change',  'input[type=file]', 'changeHandler'],
        ['drop',    'label',            'dropHandler'],
        ['dragover','label',            'dragHandler']
      ];

      for(var i in events){
        this.$el.on(events[i][0], events[i][1], $.proxy(this[events[i][2]], this) );
      }
    };

    return fileHandler;

  })();

  if (window.File && window.FileReader && window.FileList && window.Blob){
    var file = new FileHandler({
      el : '.form-file-upload'
    });
  }

})(window, document, jQuery);
