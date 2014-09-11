#!/usr/bin/env python


from json import dumps

from bottle import get, run, request, response, static_file
from py2neo import Graph


graph = Graph("http://localhost:7474/db/data/")
cypher = graph.cypher


@get("/")
def get_index():
    return static_file("index.html", root="static")


@get("/graph")
def get_graph():
    results = cypher.execute("MATCH (m:Movie)<-[:ACTED_IN]-(a:Person) "
                             "RETURN m.title as movie, collect(a.name) as cast "
                             "LIMIT {limit}", {"limit": request.query.get("limit", 100)})
    nodes = []
    rels = []
    i = 0
    for record in results.data:
        nodes.append({"title": record.get("movie"), "label": "movie"})
        target = i
        i += 1
        for name in record.get("cast"):
            actor = {"title": name, "label": "actor"}
            try:
                source = nodes.index(actor)
            except ValueError:
                nodes.append(actor)
                source = i
                i += 1
            rels.append({"source": source, "target": target})
    return {"nodes": nodes, "links": rels}


@get("/search")
def get_search():
    try:
        q = request.query["q"]
    except KeyError:
        return []
    else:
        results = cypher.execute("MATCH (movie:Movie) "
                                 "WHERE movie.title =~ {title} "
                                 "RETURN movie", {"title": "(?i).*" + q + ".*"})
        response.content_type = "application/json"
        return dumps([{"movie": record.get("movie").properties} for record in results.data])


@get("/movie/<title>")
def get_movie(title):
    results = cypher.execute("MATCH (movie:Movie {title:{title}}) "
                             "OPTIONAL MATCH (movie)<-[r]-(person:Person) "
                             "RETURN movie.title as title,"
                             "collect([person.name, head(split(lower(type(r)),'_')), r.roles]) as cast "
                             "LIMIT 1" , {"title": title})
    record = results.data[0]
    return {"title": record.get("title"),
            "cast": [dict(zip(("name", "job", "role"), member)) for member in record.get("cast")]}


if __name__ == "__main__":
    run(port=8080)

