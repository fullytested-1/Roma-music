using System.Net;
using System.Text;

var port=int.TryParse(Environment.GetEnvironmentVariable("CSHARP_PORT"),out var value)?value:8005;
using var listener=new HttpListener();
listener.Prefixes.Add($"http://0.0.0.0:{port}/");
listener.Start();
while(true){var context=await listener.GetContextAsync();var body=Encoding.UTF8.GetBytes("{\"service\":\"admin\",\"status\":\"ok\"}");context.Response.ContentType="application/json";context.Response.ContentLength64=body.Length;await context.Response.OutputStream.WriteAsync(body);context.Response.Close();}
