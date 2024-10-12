'''实例化知识图谱对象'''
from config.config import Config
from py2neo import Graph, NodeMatcher, RelationshipMatcher, ConnectionUnavailable

class GraphDao(object):

    def __init__(self):
        # 读取yaml配置
        self.__url = Config.get_instance().get_with_nested_params("database", "neo4j", "url")
        self.__username = Config.get_instance().get_with_nested_params("database", "neo4j", "username")
        self.__password = Config.get_instance().get_with_nested_params("database", "neo4j", "password")
        self.__connect_graph()

        # 创建节点匹配器
        self.__node_matcher = NodeMatcher(self.__graph) if self.__graph else None

        # 创建关系匹配器
        self.__relationship_matcher = RelationshipMatcher(self.__graph) if  self.__graph else None

    @staticmethod
    def ensure_connection(function):
        def wrapper(*args, **kwargs):
            if not args[0].__graph:
                return None
            return function(*args, **kwargs)

        return wrapper

    def __connect_graph(self):
        try:
            self.__graph = Graph(self.__url, auth=(self.__username, self.__password))
        except ConnectionUnavailable as e:
            self.__graph = None
    
    @ensure_connection
    def query_relationship_by_name(self, entity_name: str):
        # 编写 Cypher 查询语句，查询指定实体作为起始或目标节点的所有关系
        query = """
        MATCH (a)-[r]-(b)
        WHERE a.名称 = $entity_name
        RETURN a,r,b
        """
        # 执行查询，并将查询结果返回
        result = self.__graph.run(query, entity_name=entity_name).data()
        return result
    
    @ensure_connection
    def query_node(self, *label, **properties):
        return self.__node_matcher.match(*label, **properties)
