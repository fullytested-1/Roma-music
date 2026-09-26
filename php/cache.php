<?php
declare(strict_types=1);
header('Content-Type: application/json');
$db=new PDO('sqlite:'.(__DIR__.'/../data/roma.db'));$db->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);
$db->exec('CREATE TABLE IF NOT EXISTS php_cache(cache_key TEXT PRIMARY KEY,payload TEXT NOT NULL,expires_at INTEGER NOT NULL)');
$key=$_GET['key']??'';if(!$key){http_response_code(400);echo json_encode(['error'=>'key required']);exit;}
$s=$db->prepare('SELECT payload FROM php_cache WHERE cache_key=? AND expires_at>?');$s->execute([$key,time()]);$r=$s->fetch(PDO::FETCH_ASSOC);echo json_encode($r?['hit'=>true,'data'=>json_decode($r['payload'],true)]:['hit'=>false]);
?>