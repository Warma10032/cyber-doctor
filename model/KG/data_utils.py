from dataclasses import dataclass,field
from config.config import Config
from kg.Graph import GraphDao


@dataclass
class NodeEntities(object):
    # 该类负责与Graph类交互，获取节点信息

    dao: GraphDao = field(default_factory=lambda: GraphDao(), init=True, compare=False)

    # 获取节点
    def get_entities_iterator(self):

        # 定义你要查询的标签类型，比如疾病、症状、药物等
        labels_to_query = Config.get_instance().get_with_nested_params("database", "neo4j", "node-label")

        node_list = []

        # 动态查询不同标签类型的节点
        for label in labels_to_query:
            # 查询带有特定标签的节点
            nodes = self.dao.query_node(label)

            for node in nodes:
                # 根据节点的标签和属性创建字典
                node_dict = {
                    'label': label,  # 使用当前查询的标签
                    **dict(node)  # 解包节点的属性
                }
                node_list.append(node_dict)

        return node_list
        
       
    def __call__(self, *args, **kwargs):
        return self.get_entities_iterator()
