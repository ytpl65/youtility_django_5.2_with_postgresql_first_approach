def get_column_config(name):
    config = {
        'typeassist':{
            'columns':[
                {'data':'id', 'visible':False, 'defaultContent':None},
                {'data':'taname', 'title':'Name'},
                {'data':'tacode', 'title':'Code'},
                {'data':'tatype', 'title':'Type'},
                {'data':'bu', 'title':'BV'},
                {'data':'client', 'title':'Client'},
                {'data':'tenant', 'title':'tenant'},  
            ],        
        }
    }