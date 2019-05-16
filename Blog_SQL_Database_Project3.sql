CREATE Queries

CREATE keyspace blogplatform with replication = {'class' : 'SimpleStrategy', 'replication_factor': 1 };
CREATE TABLE articles(article_id int,article_title TEXT,article_content TEXT,year bigint, createstamp TIMESTAMP,updatestamp TIMESTAMP,url TEXT,user_name TEXT,
                comments list<frozen<map<timestamp,frozen<map<text,text>>>>>, tags frozen<set<TEXT>>, PRIMARY KEY(year, article_id, createstamp)) WITH CLUSTERING ORDER BY(article_id DESC, createstamp DESC);
CREATE INDEX ON articles(article_id);
create index on articles(FULL(tags));
CREATE TABLE users(user_id INT,user_name TEXT,password TEXT,active_status INT, PRIMARY KEY(user_name));

INSERT Queries

insert into articles(article_id,article_title,article_content,year,createstamp,updatestamp,url,user_name,comments,tags)  values(1,'article1','articlecontent1',2019,dateof(now()),dateof(now()),'http://locahost/article/1','kunal',[{dateof(now()):{'kunal':'comment1'}}],{'tag3','tag4'});
insert into articles(article_id,article_title,article_content,year,createstamp,updatestamp,url,user_name,comments,tags)  values(2,'article2','articlecontent2',2019,dateof(now()),dateof(now()),'http://locahost/article/2','kunal',[{dateof(now()):{'kunal':'comment2'}}],{'tag3','tag4'});
insert into articles(article_id,article_title,article_content,year,createstamp,updatestamp,url,user_name,comments,tags)  values(3,'article3','articlecontent3',2019,dateof(now()),dateof(now()),'http://locahost/article/3','kunal',[{dateof(now()):{'kunal':'comment3'}}],{'tag3','tag4'});
insert into articles(article_id,article_title,article_content,year,createstamp,updatestamp,url,user_name,comments,tags)  values(4,'article4','articlecontent4',2019,dateof(now()),dateof(now()),'http://locahost/article/4','kunal',[{dateof(now()):{'kunal':'comment4'}}],{'tag3','tag4'});
select * from articles;
delete from articles where year=2019 and article_id=4 and updatestamp='2019-05-11 17:48:34.673';
UPDATE articles SET comments = [{dateof(now()):{'Parag':'Nahi yetey kahi'}}] + comments where article_id=3 and year=2019 and createstamp = '2019-05-11 22:40:31.982';

select comments from articles where year=2019 and article_id=4 and updatestamp='2019-05-11 17:43:09.646';
delete comments[0] from articles where year = 2019 and artile_id=2 and createstamp='2019-05-11 22:40:23.094'; 