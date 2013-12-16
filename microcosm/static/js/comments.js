(function(){

  var Comments = (function(){

    var comments = function(options){

      this.$el = false;
      if(typeof options.el !== "undefined"){
        this.$el = $(options.el);
      }

      this.defaultContainer = false;
      if(typeof options.defaultContainer !== "undefined"){
        this.defaultContainer = $(options.defaultContainer);
      }

      this.template = false;
      if(typeof options.template !== "undefined"){
        this.template = options.template;
      }

      this.stack = [];
      this.bind();
    };

    comments.prototype.cleanup = function(e){

      var view;

      for(var i=0,j=this.stack.length;i<j;i++){
        view = this.stack.pop();
        view.off().remove();
      }

      var oldInstances = this.$el.find('.insertReplyBox.active');

      if (oldInstances.length > 0){
        for( i=0,j=oldInstances.length;i<j;i++){

          if (typeof oldInstances[i].$ !== "undefined" &&
              typeof oldInstances[i].$.comment_box !== "undefined" &&
              oldInstances[i].$.comment_box){

            oldInstances[i].$.comment_box.remove();
            oldInstances[i].$.comment_box = false;
            oldInstances.removeClass('active');
          }
        }
      }

    };

    comments.prototype.toggleDefaultContainer = function(){

      if (this.stack.length > 0){
        this.defaultContainer.hide();
      }else{
        this.defaultContainer.show();
      }

    };

    comments.prototype.generateNewInstanceCommentBox = function(e){

      var instance = $( this.template );

      this.cleanup();

      instance.simpleEditor = new simpleEditor({
        el : instance
      });

      this.stack.push(instance);

      return instance;
    };

    comments.prototype.clickHandler = function(e){

      var _this    = e.currentTarget;

      if (typeof _this.$ == 'undefined'){
        _this.$  = $(_this);
      }

      if (!_this.$.hasClass('active')){

        _this.$.comment_box = $('<div class="generated-comment-box"></div>');
        _this.$.comment_box.append( this.generateNewInstanceCommentBox() );

        _this.$
          .addClass('active')
          .after( _this.$.comment_box );
      }else{
        console.log(_this.$);
        _this.$.comment_box.toggle();
      }
      this.toggleDefaultContainer();

    };

    comments.prototype.bind = function(){

      var events = [
        ['click', '.insertReplyBox', 'clickHandler']
      ];

      for(var i in events){
        this.$el.on(events[i][0], events[i][1], $.proxy(this[events[i][2]], this) );
      }

    };

    return comments;

  })();

  new Comments({
    el               : '.content-body',
    defaultContainer : '.reply-container',
    template         : $('.reply-container .comment-item-body').html().trim()
  });

})();