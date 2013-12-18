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

    comments.prototype.generateNewInstanceCommentBox = function(options){

      var fragment = $( this.template ),
          replyto_id = "";

      if(typeof options.ref !== 'undefined'){
        replyto_id = options.ref;
      }
      fragment.find('input[name=inReplyTo]').val(replyto_id);

      console.log('replyTo_id', replyto_id);
      console.log(fragment.find('input[name=inReplyTo]').val());

      this.cleanup();

      fragment.simpleEditor = new simpleEditor({
        el : fragment
      });

      this.stack.push(fragment);

      return fragment;
    };

    comments.prototype.fetchCommentSource = function(comment_id){

      // FIXME: possible bug with relative path, need to get absolute
      return $.ajax({
        url  : 'comments/'+comment_id+"/source",
        type : 'GET'
      });

    };


    comments.prototype.clickHandler = function(e){

      var _this = e.currentTarget,
          commentBoxOptions;

      if (typeof _this.$ == 'undefined'){
        _this.$  = $(_this);
      }

      commentBoxOptions = {
        ref   : _this.$.attr('data-ref') || ""
      };

      if (!_this.$.hasClass('active')){

        _this.$.comment_box = $('<div class="generated-comment-box"></div>');
        _this.$.comment_box.append( this.generateNewInstanceCommentBox(commentBoxOptions) );

        _this.$
          .addClass('active')
          .after( _this.$.comment_box );

        // FIXME: not flexible, could be better
        if(_this.$.attr('data-comment-id')){

          _this.$.comment_box.find('textarea').attr('placeholder','Loading... Please wait...');

          this.fetchCommentSource(_this.$.attr('data-comment-id'))
              .success($.proxy(function(response){
                this.$.comment_box
                      .find('textarea')
                      .attr('placeholder','Enter your text here...')
                      .val(response.data.markdown);
              },_this))
              .error($.proxy(function(){
                this.$.comment_box
                      .find('textarea')
                      .attr('placeholder','Enter your text here...');
              },_this));
        }

      }else{
        this.cleanup();
      }
      this.toggleDefaultContainer();

    };

    comments.prototype.reset = function(){
      this.cleanup();
      this.toggleDefaultContainer();
    };

    comments.prototype.bind = function(){

      var events = [
        ['click', '.insertReplyBox', 'clickHandler'],
        ['reset', 'form',            'reset']
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