# 对于一个完整的tracking tree：追踪其周期变化过程， 如果周期出现错误，尝试依据细胞分裂的过程来纠正细胞的周期准确性
import os.path
from typing import List
import json
import random
import pickle
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from tracker import Tracker, CellNode, TrackingTree


# TODO 将解析好的细胞信息写回annotation.json文件中，包括细胞的代系，周期，追踪信息等等
# TODO 对解析好的信息，生成统计信息，包括每个细胞的分裂次数，周期长短，arrest情况


class TreeParser(object):
    """解析TrackingTree"""

    def __init__(self, track_tree: TrackingTree):
        self.tree = track_tree

        self.lineage_dict = {}
        # {cells: [children_list], branch_id: ''， 'G1_start': '', 'S_start': '', 'G2_start': '', 'M1_start': '', 'M2_start': ''}

        self.root_parent_list = [self.tree.nodes.get(self.tree.root)]
        self.parse_root_flag = False
        self.parse_mitosis_flag = {}
        self.parse_s_flag = {}

        self.__division_count = 0

    def record_cell_division_count(self):
        self.__division_count += 1
        return self.__division_count

    def get_child(self, parent: CellNode) -> List[CellNode]:
        """根据父节点返回全部子节点，只包含直系子节点"""
        return self.tree.children(parent.identifier)

    def search_root_node(self):
        """
        寻找细胞每一代的根节点，即TrackingTree每一个分支的第一个节点
        此方法是为了处理发生有丝分裂的情况, 即tree开始出现分支
        当细胞开始发生有丝分裂的时候，tree会产生分裂，此时记录该节点，并回溯，作为一代细胞
        """
        branch_id = 0
        root_node = self.tree.nodes.get(self.tree.root)
        root_node.cell.set_cell_id(str(self.tree.track_id) + '_' + str(branch_id))
        self.lineage_dict[root_node] = {'cells': [root_node], 'branch_id': root_node.cell.branch_id, 'parent': None}
        if self.tree.root is None:
            return
        else:
            loop_queue = [root_node]
            while loop_queue:  # 主循环
                current = loop_queue.pop(0)
                ch = self.get_child(current)
                for next_node in ch:
                    loop_queue.append(next_node)
                if len(ch) > 1:
                    self.record_cell_division_count()
                    if current not in self.lineage_dict:
                        for child_cell in ch:
                            self.lineage_dict[child_cell] = {'cells': [child_cell],
                                                             'branch_id': child_cell.cell.branch_id,
                                                             'branch_start': child_cell.cell.frame, 'parent': current}
                            if child_cell not in self.root_parent_list:
                                branch_id += 1
                                child_cell.cell.set_cell_id(str(self.tree.track_id) + '_' + str(branch_id))
                                self.root_parent_list.append(child_cell)
        self.parse_root_flag = True

    def parse_lineage(self, root_node):
        """获取每一个分支所包含的细胞node序列"""
        loop_queue = [root_node]
        last_node = None
        while loop_queue:  # 主循环
            current_node = loop_queue.pop(0)
            last_node = current_node
            ch = self.get_child(current_node)
            for loop_node in ch:
                loop_queue.append(loop_node)
            if current_node not in self.lineage_dict[root_node].get('cells'):
                self.lineage_dict[root_node].get('cells').append(current_node)
            if len(ch) > 1:
                break
        self.lineage_dict[root_node]['branch_end'] = last_node.cell.frame + 1

    def get_lineage_dict(self):
        if not self.parse_root_flag:
            self.search_root_node()
        for root in self.root_parent_list:
            self.parse_lineage(root)
            self.parse_mitosis_flag[root] = False
        return self.lineage_dict

    def bfs(self):
        """按照广度优先遍历TrackingTree"""
        root_node = self.tree.nodes.get(self.tree.root)
        if self.tree.root is None:
            return
        else:
            loop_queue = [root_node]
            while loop_queue:  # 主循环
                current = loop_queue.pop(0)
                ch = self.get_child(current)
                for loop_node in ch:
                    loop_queue.append(loop_node)
                yield ch

    @staticmethod
    def check_mitosis_start(start_index, lineage_cell, area_size_t=0.9, mitosis_gap=20, m_predict_threshold=2):
        """检查M期进入的情况，如果面积符合条件，则检查下一帧，如果下一帧面积过小，则不认为进入了，判定为分割误判,
        如果检查通过，则随机检查接下来3-6帧，如果预测为M期的数量大于等于2，则判定进入M期通过，否则，判定失败
        如果离上一次进入M期间隔过短，同样认为是误判。
        """
        predict_enter_cell = lineage_cell[start_index]
        next_cell = lineage_cell[start_index + 1]
        if lineage_cell[0].cell.phase == 'M' and start_index < mitosis_gap:
            return False
        elif next_cell.cell.area / predict_enter_cell.cell.area < area_size_t:
            return False
        else:
            predict_m_count = 0
            if len(lineage_cell) - start_index < 5:
                return True
            for i in range(min(5, len(lineage_cell) - start_index)):
                if lineage_cell[start_index + i].cell.phase == 'M':
                    predict_m_count += 1
            if predict_m_count >= m_predict_threshold:
                return True
            else:
                return False

    @staticmethod
    def check_s_start(start_index, linage_cell, threshold=3):
        """
        检查S期的进入，如果该细胞预测为S期，则随机往后检查5帧，
        剩余帧数不满5帧，则检查全部剩余帧数，如果累计预测S期大于threshold，
        则判定成功，否则，判定失败
        """
        s_count = 0
        if linage_cell[start_index].cell.phase == 'S':
            for i in range(min(5, len(linage_cell) - start_index)):
                if linage_cell[start_index + i].cell.phase == 'S':
                    s_count += 1
        if s_count >= threshold:
            return True
        return False

    @staticmethod
    def check_s_exit(end_index, linage_cell, threshold=3):
        """判断S期退出，判断原理同进入S期，如果细胞开始退出S期，则往后检查"""
        non_s_count = 0
        if linage_cell[end_index].cell.phase != 'S':
            for i in range(min(5, len(linage_cell) - end_index)):
                if linage_cell[end_index + i].cell.phase != 'S':
                    non_s_count += 1
            if non_s_count >= threshold:
                return True
            return False

    def parse_mitosis(self, lineage: dict, root: CellNode, lineage_index=None):
        """
        解析mitosis的进入和退出
        """
        area_size_t = 1.4  # 判断M期的进入
        cell_node_line = lineage.get('cells')
        mitosis_start_index = None
        exist_m_frame = 0
        for i in range(len(cell_node_line) - 1):
            before_cell_node = cell_node_line[i]
            current_cell_node = cell_node_line[i + 1]
            # print(f'{current_cell_node.cell.area / before_cell_node.cell.area:.2f}')
            if before_cell_node.cell.phase == 'M':
                exist_m_frame += 1
            if current_cell_node.cell.area / before_cell_node.cell.area >= area_size_t:
                if self.check_mitosis_start(i, cell_node_line):
                    mitosis_start_index = i + 1
                    break
            elif before_cell_node.cell.phase == 'M' and current_cell_node.cell.area / before_cell_node.cell.area < area_size_t:
                if self.check_mitosis_start(i, cell_node_line, m_predict_threshold=3):
                    mitosis_start_index = i
                    break
        if mitosis_start_index is None:
            # 两种情况， 第一种是细胞进入M期之后才开始追踪， 第二种是细胞已经完成分裂但是还没有进入到下一个M期
            if len(cell_node_line) < 5:
                if exist_m_frame >= 2:
                    for cell_node in cell_node_line:
                        cell_node.cell.phase = 'M'
                    lineage['m2_start'] = 0
            else:
                if lineage_index != 0:
                    for cell_node in cell_node_line[: 3]:
                        cell_node.cell.phase = 'M'
                    lineage['m1_start'] = 0
        else:
            # 细胞正常从G1-G2的任意时期进入M期
            for m_index in range(mitosis_start_index, len(cell_node_line)):
                cell_node_line[m_index].cell.phase = 'M'
            lineage['m2_start'] = mitosis_start_index
        self.parse_mitosis_flag[root] = True

    def parse_s(self, lineage: dict, root: CellNode, lineage_index=None):
        """判断S期的进入"""
        cell_node_line = lineage.get('cells')
        s_start_index = None
        s_exit_index = None
        if not self.parse_mitosis_flag[root]:
            self.parse_mitosis(lineage, root, lineage_index=lineage_index)
        if lineage.get('m1_start') is not None:
            check_start = lineage.get('m1_start')
        else:
            check_start = 0
        for cell_node_index in range(check_start, len(cell_node_line)):
            if cell_node_line[cell_node_index].cell.phase == 'S':
                if self.check_s_start(cell_node_index, cell_node_line):
                    lineage['s_start'] = s_start_index = cell_node_index
                    break
        if s_start_index is not None:
            for cell_node_index_2 in range(s_start_index, len(cell_node_line)):
                if cell_node_line[cell_node_index_2].cell.phase != 'S':
                    if self.check_s_exit(cell_node_index_2, cell_node_line):
                        lineage['s_exit'] = s_exit_index = cell_node_index_2
                        break

        if s_start_index is not None:
            if s_exit_index is not None:
                end = s_exit_index
            else:
                end = len(cell_node_line)
            for cell_node_index_s in range(s_start_index, end):
                cell_node_line[cell_node_index_s].cell.phase = 'S'
        self.parse_s_flag[root] = True

    def parse_g1_g2(self, lineage: dict, root: CellNode, lineage_index=None):
        """将G1/G2准确区分为G1，G2"""
        cell_node_line = lineage.get('cells')
        g1_start_index = None
        g1_exit_index = None
        g2_start_index = None
        g2_exit_index = None
        m1_start = lineage.get('m1_start')
        m2_start = lineage.get('m2_start')
        if not self.parse_s_flag[root]:
            self.parse_s(lineage, root)
        if lineage.get('s_start') is not None:  # 细胞进入了S期
            # 1. track从s期开始的
            # 2. track从G1期开始的
            # 3. track从M1期开始的
            g1_exit_index = lineage.get('s_start')
            if m1_start is not None:
                g1_start_index = 3
            else:
                g1_start_index = 0
            if lineage.get('s_exit') is not None:
                g2_start_index = lineage.get('s_exit')
                if m2_start is not None:
                    g2_exit_index = m2_start
                else:
                    g2_exit_index = len(cell_node_line)

        else:  # 细胞没有经历S期
            # 1. track从M1期开始，没有进入S期
            # 2. track从G1期开始， 没有进入S期
            # 3. track从G2期开始, 进入M2期
            # 3. track从G2期开始, 没有进入M2期
            if m2_start is not None:
                if len(cell_node_line) > 5:  # 细胞进入M期，还没有分裂，此时定义为M2期
                    g2_start_index = 0
                    g2_exit_index = m2_start
            elif m1_start is not None:  # 细胞已经完成分裂，还没退出M期， 此时定义为M1期
                g1_start_index = 3
                g1_exit_index = len(cell_node_line)
            else:
                if len(cell_node_line) > 10:
                    if lineage_index == 0:  # 初代细胞
                        g1_start_index = 0
                        g1_exit_index = len(cell_node_line)
                    else:  # 次代细胞
                        g2_start_index = 0
                        g2_exit_index = len(cell_node_line)
                else:
                    g1_start_index = 0
                    g1_exit_index = len(cell_node_line)

        if g1_start_index is not None:
            lineage['g1_start'] = g1_start_index
            if g1_exit_index is not None:
                end = g1_exit_index
            else:
                end = len(cell_node_line)
            for cell_node_index_g1 in range(g1_start_index, end):
                cell_node_line[cell_node_index_g1].cell.phase = 'G1'
        if g2_start_index is not None:
            lineage['g2_start'] = g2_start_index
            if g2_exit_index is not None:
                end_2 = g2_exit_index
            else:
                end_2 = len(cell_node_line)
            for cell_node_index_g2 in range(g2_start_index, end_2):
                cell_node_line[cell_node_index_g2].cell.phase = 'G2'

    def set_cell_id(self, lineage: dict, root: CellNode, linage_index):
        cell_node_line = lineage.get('cells')
        branch_id = linage_index
        cell_id = str(self.tree.track_id) + '_' + str(branch_id)
        if linage_index == 0:
            root.cell.set_cell_id(cell_id)
            lineage['parent'] = root
        else:
            parent = lineage['parent']
            parent.cell.set_cell_id(parent.cell.cell_id)
        for cell_node in cell_node_line:
            cell_node.cell.set_cell_id(cell_id)
            cell_node.cell.set_track_id(self.tree.track_id, 1)

    def parse_lineage_phase(self, lineage: dict, root: CellNode, linage_index):
        root = root
        self.parse_mitosis(lineage, root, linage_index)
        self.parse_s(lineage, root, linage_index)
        self.parse_g1_g2(lineage, root, linage_index)
        self.set_cell_id(lineage, root, linage_index)


def pares_single_tree(tree: TrackingTree):
    parser = TreeParser(tree)
    parser.search_root_node()
    parser.get_lineage_dict()
    for node_index in range(len(parser.root_parent_list)):
        cell_lineage = parser.lineage_dict.get(parser.root_parent_list[node_index])
        parser.parse_lineage_phase(cell_lineage, root=parser.root_parent_list[node_index], linage_index=node_index)
    return parser


def run_track(annotation, track_range=None, dic=None, mcy=None):
    tracker = Tracker(annotation, dic=dic, mcy=mcy)
    if track_range:
        tracker.track(range=track_range)
    else:
        tracker.track()
    parser_dict = {}
    for tree in tracker.trees:
        parser = pares_single_tree(tree)
        parser_dict[tree] = parser
    tracker.parser_dict = parser_dict
    return tracker


def track_tree_to_table(tracker: Tracker, filepath):
    """导出track result到table中"""
    track_detail_columns = ['frame_index', 'track_id', 'cell_id', 'parent_id', 'center_x', 'center_y', 'phase',
                            'mask_of_x_points', 'mask_of_y_points']
    track_detail_dataframe = pd.DataFrame(columns=track_detail_columns)

    def generate_series(cell_lineage):
        cell_nodes = cell_lineage.get('cells')
        parent = cell_lineage.get('parent')
        series_list = []
        for node in cell_nodes:
            col = [node.cell.frame, node.cell.track_id,
                   node.cell.cell_id, parent.cell.cell_id,
                   node.cell.center[0], node.cell.center[1],
                   node.cell.phase,
                   node.cell.position[0], node.cell.position[1]]
            s = pd.Series(dict(zip(track_detail_columns, col)))
            series_list.append(s)
        return series_list

    parser_dict = tracker.parser_dict
    for tree in parser_dict:
        parser = parser_dict[tree]
        for node_index in parser.root_parent_list:
            cell_lineage = parser.lineage_dict.get(node_index)
            series_list = generate_series(cell_lineage)
            for series in series_list:
                track_detail_dataframe = track_detail_dataframe.append(series, ignore_index=True)
    if os.path.exists(filepath):
        fname = os.path.join(os.path.dirname(filepath), '(new)' + os.path.basename(filepath))
    else:
        fname = filepath
    track_detail_dataframe.to_csv(fname, index=False)


def track_trees_to_json(tracker: Tracker):
    """track结果导出到json文件中"""
    pass


def run(annotation, output_table, track_range=None, save_visualize=False, visualize_file=None, dic=None, mcy=None, track_to_json=False):
    tracker = run_track(annotation, track_range=track_range, dic=dic, mcy=mcy)
    track_tree_to_table(tracker, output_table)
    if save_visualize:
        tracker.visualize_to_tif(mcy_img, visualize_file, tracker.trees, xrange=track_range)
    if track_to_json:
        track_trees_to_json(tracker)

if __name__ == '__main__':
    annotation = r'G:\20x_dataset\copy_of_xy_01\copy_of_1_xy01-sub-id-center.json'
    mcy_img = r'G:\20x_dataset\copy_of_xy_01\raw\sub_raw\mcy\copy_of_1_xy01.tif'
    dic_img = r'G:\20x_dataset\copy_of_xy_01\raw\sub_raw\dic\copy_of_1_xy01.tif'
    table = r'G:\20x_dataset\copy_of_xy_01\development-dir\track-table-test.csv'
    visual = r'G:\20x_dataset\copy_of_xy_01\development-dir\tracking_visualize-test.tif'
    # tracker = Tracker(mcy_img, dic_img, annotation)
    run(annotation, table, save_visualize=True, visualize_file=visual, track_range=50)

    # tracker = run(annotation, 50)
    #
    # track_tree_to_table(tracker, table)
    # tracker.save_visualize(368, tracker.trees)
    # tracker.visualize_to_tif(mcy_img, visual, tracker.trees, 50)

    # tracker = Tracker(annotation)
    # tracker.track(50)
    # tree = tracker.trees[10]
    # # print(tree)
    # parse = TreeParser(tree)
    # parse.search_root_node()
    #
    # d = parse.get_lineage_dict()
    # # for node_index in range(len(parse.root_parent_list)):
    # for node_index in range(3):
    #     cell_lineage = parse.lineage_dict.get(parse.root_parent_list[node_index])
    #     # print(cell_lineage)
    #     parse.parse_lineage_phase(cell_lineage, root=parse.root_parent_list[node_index], linage_index=node_index)
    #     print(len(cell_lineage.get('cells')))
    #     print('***' * 10)
    #
    #     # break
    # tracker.save_visualize(250, tree)
