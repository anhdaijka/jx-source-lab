SELECT dialogue_key,task_key,npc_key,phase,language,text FROM dialogues WHERE text LIKE '%' || :term || '%' ORDER BY task_key,id;
