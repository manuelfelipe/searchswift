# Search Middleware for Swift

A middleware provider for Swift that gives Swift the ability to send metadata events
to a queue system (rabbitmq initially) for further analysis. In the context of this middleware the queue messages are use to forward them to a search engine (elasticsearch for an initial PoC).

## Flow
 - swift post metadata
   - swift search middleware hit
     - msg push to rabbitmq with object metadata
       - logstash monitoring / pulling for msgs in search queue
         - logstash forward payload to EL
           - Elastic search index the document

## build
```
 $ sudo python setup.py install
```
## Enable Middleware for Swift
```
  # / etc/swift/proxy-server.conf

    [pipeline:main]
    pipeline = catch_errors cache tempauth *searchmiddleware* proxy-server

  # And add a searchmiddleware filter section

    [filter:searchmiddleware]
    use = egg:searchswift#searchmiddleware
    amqp_connection = amqp://guest:guest@localhost/
    # amqp_exchange = swiftsearch  # (optional) exchange name for messaging
    # amqp_exchange_type = direct  # (optional) type of exchange to create in rabbitmq
    # amqp_exchange_durable = True # (optional) true or false

```

then restart swift proxy service

## Trying it out

- download and execute elasticsearch in your machine.

```
# query for all documents. should be empty initially
$ curl -XGET "http://localhost:9200/_search?pretty" 
```

```
# upload a file to swift. Local LICENSE file to yp container
$ swift upload yp LICENSE 
```

```
# set some metadata for the uploaded object
$ swift post yp LICENSE --meta k1:v1 --meta k2:v2 --meta last_name:correa
```

```
- check rabbitmq exchanges and queues definitions. Should have a swiftsearch exchange with a search queue and at least one message in the queue with something like:

{  
   "path":"/v1/AUTH_697a600672d5486e9c0e64034bc84845/yp/LICENSE",
   "id":"L3YxL0FVVEhfNjk3YTYwMDY3MmQ1NDg2ZTljMGU2NDAzNGJjODQ4NDUveXAvTElDRU5TRQ==",
   "metadata":{  
      "X-User":"demo",
      "X-User-Id":"ee98e9ff3909444d8c4c0e4882b5b4a3",
      "X-Object-Meta-K2":"v2",
      "X-Object-Meta-Last-Name":"correa",
      "X-Object-Meta-K1":"v1",
      "X-Tenant-Name":"demo",
      "X-Tenant-Id":"697a600672d5486e9c0e64034bc84845"
   }
}
```

- download logstash to act as a forwarder from rmq to el

```
# run logstash to collect input msgs from rmq and send to EL and stdout (for debug)
$ bin/logstash -e 'input { rabbitmq { host => "10.211.55.5" queue => search durable => true } } output { elasticsearch { host => localhost index => swift document_id => "%{id}" document_type => object } stdout { } }'
```

```
# try again getting the list of documents in EL. should have at least one indexed doc now.
$ curl -XGET "http://localhost:9200/_search?pretty" # query for all documents. 
{  
   "took":28,
   "timed_out":false,
   "_shards":{  
      "total":5,
      "successful":5,
      "failed":0
   },
   "hits":{  
      "total":1,
      "max_score":1.0,
      "hits":[  
         {  
            "_index":"swift",
            "_type":"object",
            "_id":"L3YxL0FVVEhfNjk3YTYwMDY3MmQ1NDg2ZTljMGU2NDAzNGJjODQ4NDUveXAvTElDRU5TRQ==",
            "_score":1.0,
            "_source":{  
               "path":"/v1/AUTH_697a600672d5486e9c0e64034bc84845/yp/LICENSE",
               "id":"L3YxL0FVVEhfNjk3YTYwMDY3MmQ1NDg2ZTljMGU2NDAzNGJjODQ4NDUveXAvTElDRU5TRQ==",
               "metadata":{  
                  "X-User":"demo",
                  "X-User-Id":"ee98e9ff3909444d8c4c0e4882b5b4a3",
                  "X-Object-Meta-K2":"v2",
                  "X-Object-Meta-Last-Name":"correa",
                  "X-Object-Meta-K1":"v1",
                  "X-Tenant-Name":"demo",
                  "X-Tenant-Id":"697a600672d5486e9c0e64034bc84845"
               },
               "@version":"1",
               "@timestamp":"2015-05-22T19:03:01.436Z"
            }
         }
      ]
   }
}

```

## TODO

 - configurable headers list for capture
 - message timeout ?
 - endpoint to forward search to the selected and configurable search engine
 - elasticsearch push back to object metadata to flag it as Indexed
 - async check of not indexed files
 - tests ?

## Development Status
This software is still in planning / playaround stage, many things could and will change.
