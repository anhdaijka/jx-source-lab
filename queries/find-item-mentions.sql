SELECT item_key,name_cn,name_vi,item_type,description FROM items WHERE name_cn LIKE '%'||:term||'%' OR name_vi LIKE '%'||:term||'%' OR description LIKE '%'||:term||'%';
