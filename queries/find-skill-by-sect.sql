SELECT skill_key,name_cn,name_vi,route_key,level_req,description FROM skills WHERE sect_key=:sect_key ORDER BY CAST(level_req AS INTEGER),skill_key;
