// exmaple usage:
//  new Filters({
//    el     : '.metabar-filters',
//    query  : 'grizzly bears', /*current_user_searched_query*/
//    url : '/search/?q=$1' /*only supports '$1' as a match*/
//  });
//
// filters assumed in the form of <input type="checkbox" name="ABC" value="123"> which ouput "ABC:123"

(function(){

  var Filters = (function(){

    var filters = function(options){

      options.query = decodeURIComponent(options.query)

      if(typeof options.el !== 'undefined'){
        this.$el = $(options.el);
      }

      if(typeof options.query !== 'undefined'){
        // replaces existing params
        this.query = options.query.replace(/\s?\w+:\w+/g,'');
      }

      if(typeof options.url !== 'undefined'){
        this.url = options.url;
      }

      this.filters = this.$el.find('input');

      this.bind();
      return this;
    };

    filters.prototype.parse = function(){

      var params  = [],
          checked = this.filters.filter(':checked');

      for(var i=0,j=checked.length;i<j;i++){
        params.push( [checked[i].name,checked[i].value].join(':') );
      }

      return params.join('+');
    };

    filters.prototype.changeHandler = function(){

      var params          = this.parse(),
          new_query       = this.query + (params.length>0 ? '+' + params : ''),
          formatted_query = this.url.replace(/\$1/g, new_query);

      window.location.href = formatted_query;
    };

    filters.prototype.bind = function(){
      var events = [
        ['change',    'input[type=checkbox]', 'changeHandler']
      ];
      for(var i in events){
        this.$el.on(events[i][0], events[i][1], $.proxy(this[events[i][2]], this) );
      }
    };

    return filters;

  })();
  window.Filters = Filters;

})();