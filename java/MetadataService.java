import com.sun.net.httpserver.*;
import java.net.*;

public class MetadataService {
  public static void main(String[] args) throws Exception {
    int port=Integer.parseInt(System.getenv().getOrDefault("JAVA_PORT","8004"));
    var server=HttpServer.create(new InetSocketAddress(port),0);
    server.createContext("/health",exchange->{byte[] body="{\"service\":\"metadata\",\"status\":\"ok\"}".getBytes();exchange.getResponseHeaders().set("Content-Type","application/json");exchange.sendResponseHeaders(200,body.length);exchange.getResponseBody().write(body);exchange.close();});
    server.start();
  }
}
