require 'json'
require 'webrick'
port=ENV.fetch('RUBY_PORT','8003').to_i
server=WEBrick::HTTPServer.new(Port:port,AccessLog:[],Logger:WEBrick::Log.new($stderr,WEBrick::Log::WARN))
server.mount_proc('/health'){|_,res|res['Content-Type']='application/json';res.body=JSON.generate({service:'history',status:'ok'})}
server.mount_proc('/history'){|_,res|res['Content-Type']='application/json';res.body=JSON.generate({items:[]})}
trap('INT'){server.shutdown}
server.start
