# =============================================================================
# MIT License
# 
# Copyright (c) 2021 luckytyphlosion
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# =============================================================================

import itertools
import collections

class VrChange:
    __slots__ = ("old", "new")

    def __init__(self, old, new):
        self.old = old
        self.new = new

#vr_changes = (
#    VrChange(9300, 9297),
#    VrChange(9148, 

# how many diffs?
# 1 win 2
# 1 win 3
# 1 win 4
# ...
# 1 win 12
# 2 win 1
# 2 win 3
# 2 win 4
# ...
# 2 win 12
# ===
# so 12*11 diffs
# ==

def test_all_perms_len():
    result = 0

    for i in range(479001600):
        result += i
        if i % 10000000 == 0:
            print(f"i: {i}")

    print(result)
    
def get_vrs(players):
    pass
    #for player in players:
        
# Adapted from http://wiki.tockdom.com/wiki/VR
# Probably under GPLv2+
vr_diff_tab = [
      6598,  4999,  3963,  3233,  2671,  2212,  1819,  1476,
      1168,   889,   633,   395,   174,   -34,  -231,  -418,
      -596,  -767,  -931, -1090, -1243, -1392, -1536, -1676,
     -1813, -1946, -2076, -2203, -2328, -2450, -2569, -2687,
     -2802, -2915, -3026, -3136, -3243, -3349, -3454, -3557,
     -3658, -3759, -3857, -3955, -4051, -4147, -4241, -4334,
     -4425, -4516, -4606, -4695, -4783, -4870, -4957, -5042,
     -5127, -5211, -5294, -5377, -5459, -5540, -5622, -5702,
     -5783, -5863, -5942, -6022, -6101, -6180, -6259, -6338,
     -6417, -6495, -6574, -6653, -6731, -6810, -6889, -6968,
     -7048, -7127, -7207, -7287, -7367, -7448, -7530, -7611,
     -7693, -7776, -7860, -7944, -8029, -8114, -8201, -8288,
     -8377, -8466, -8557, -8649, -8743, -8838, -8935, -9034,
     -9135, -9239, -9345, -9455, -9568, -9684, -9806, -9933,
]

def get_vr_diff_by_tab(diff): # diff = VR(winner) - VR(loser)
    if diff > 6598:
        return 0
    elif diff < -9933:
        return 112

    search = diff;
    i = 0;
    j = len(vr_diff_tab) - 1

    while i < j:
        k = (i + j)//2;
        if search > vr_diff_tab[k]:
            j = k - 1
        elif search <= vr_diff_tab[k + 1]:
            i = k + 1
        else:
            return k + 1

    return i + 1

def calc_vr_diffs(initial_vrs):
    n = len(initial_vrs)
    vr_diffs = [[0] * n for i in range(n)]

    for i in range(n):
        for j in range(n):
            if i == j:
                continue

            vr_diff = get_vr_diff_by_tab(initial_vrs[i] - initial_vrs[j]);
            vr_diffs[i][j] = vr_diff;
            #std::printf("vr diff %lu (%d), %lu (%d): %d\n", i, initial_vrs[i], j, initial_vrs[j], vr_diff);

    return vr_diffs

def calc_player_vr(players_lost_against, players_won_against, vr_diffs, player_vr, player):
    resulting_vr = player_vr

    # tally up losses against other players
    for player_lost_against in players_lost_against:
        resulting_vr -= vr_diffs[player_lost_against][player]

    # then tally up wins against other players
    for player_won_against in players_won_against:
        resulting_vr += vr_diffs[player][player_won_against]

    resulting_vr = min(resulting_vr, 9999)
    return resulting_vr

class PartialPlacements:
    __slots__ = ("player", "all_players_possible_placements")

    def __init__(self, player, players_lost_against=None, players_won_against=None, all_players_possible_placements=None):
        self.player = player
        if players_lost_against is not None and players_won_against is not None:
            self.all_players_possible_placements = {}

            players_lost_against_len = len(players_lost_against)

            lost_range = frozenset(range(1, players_lost_against_len + 1))
            
            for player_lost_against in players_lost_against:
                self.all_players_possible_placements[player_lost_against] = lost_range
    
            self.all_players_possible_placements[player] = frozenset((players_lost_against_len + 1,))
    
            won_range = frozenset(range(players_lost_against_len + 2, players_lost_against_len + 2 + len(players_won_against)))
    
            for player_won_against in players_won_against:
                self.all_players_possible_placements[player_won_against] = won_range

        elif all_players_possible_placements is not None:
            self.all_players_possible_placements = all_players_possible_placements
        else:
            raise RuntimeError("One of (players_lost_against and players_won_against) or all_players_possible_placements must be specified!")

    @classmethod
    def from_lw(cls, player, players_lost_against, players_won_against):
        return cls(player, players_lost_against=players_lost_against, players_won_against=players_won_against)

    @classmethod
    def from_all_players_possible_placements(cls, player, all_players_possible_placements):
        return cls(player, all_players_possible_placements=all_players_possible_placements)

    def __repr__(self):
        player_possible_placements_to_players = collections.defaultdict(list)

        for player, player_possible_placements in self.all_players_possible_placements.items():
            player_possible_placements_to_players[player_possible_placements].append(player)

        sorted_partial_placements = [players for player_possible_placements, players in sorted(player_possible_placements_to_players.items(), key=lambda x: min(x[0]))]

        return f"{sorted_partial_placements}"

def find_player_pos(initial_vrs, player, expected_vr, vr_diffs=None):
    n = len(initial_vrs)
    players = set(range(n))
    players.remove(player)
    if vr_diffs is None:
        vr_diffs = calc_vr_diffs(initial_vrs)

    all_partial_placements = []

    for i in range(n):
        for players_lost_against in itertools.combinations(players, i):
            players_won_against = players - set(players_lost_against)
            resulting_vr = calc_player_vr(players_lost_against, players_won_against, vr_diffs, initial_vrs[player], player)
            if resulting_vr == expected_vr:
                all_partial_placements.append(PartialPlacements.from_lw(player, players_lost_against, players_won_against))

    return all_partial_placements

def output_all_partial_placements(all_partial_placements, player):
    if all_partial_placements is None:
        return f"{player} unknown (left)"
    else:
        return "\n".join(f"{partial_placements}" for partial_placements in all_partial_placements)

def find_all_player_positions(initial_vrs, expected_vrs):
    n = len(initial_vrs)
    vr_diffs = calc_vr_diffs(initial_vrs)
    all_players_all_partial_placements = []

    for i in range(n):
        expected_vr = expected_vrs[i]
        if expected_vr != -1:
            all_players_all_partial_placements.append(find_player_pos(initial_vrs, i, expected_vr, vr_diffs))
        else:
            all_players_all_partial_placements.append(None)

    #for i, all_partial_placements in enumerate(all_players_all_partial_placements):
    #    print(output_all_partial_placements(all_partial_placements, i))

    output = ""

    #for i in range(len(initial_vrs)):
    #    all_possible_placements, all_furthest_partial_placements = find_all_player_positions_helper(all_players_all_partial_placements, i)
    #    output += f"{i}: {output_all_partial_placements(all_possible_placements, i)}\n"
    #    output += f"{i} furthest: {output_all_partial_placements(all_furthest_partial_placements.values, i)}\n"

    all_possible_placements, all_furthest_partial_placements = find_all_player_positions_helper(all_players_all_partial_placements, 0)
    if len(all_possible_placements) == 0:
        # try excluding some players in case of disrepancies with a player's VR
        modified_all_players_all_partial_placements = list(all_players_all_partial_placements)
        all_players_all_possible_placements = []

        for i in range(n):
            saved_all_partial_placements = modified_all_players_all_partial_placements[i]
            modified_all_players_all_partial_placements[i] = None
            all_possible_placements, all_furthest_partial_placements = find_all_player_positions_helper(modified_all_players_all_partial_placements, 0)
            output += f"{i}: {output_all_partial_placements(all_possible_placements, i)}\n"
            output += f"{i} furthest: {output_all_partial_placements(all_furthest_partial_placements.values, i)}\n"
            modified_all_players_all_partial_placements[i] = saved_all_partial_placements
            #all_players_all_possible_placements.append(all_possible_placements)
    else:
        output += f"{i}: {output_all_partial_placements(all_possible_placements, i)}\n"
        output += f"{i} furthest: {output_all_partial_placements(all_furthest_partial_placements.values, i)}\n"

    print(output)

class AllFurthestPartialPlacements:
    __slots__ = ("num_single_slices", "values")

    def __init__(self):
        self.num_single_slices = 0
        self.values = []

def find_all_player_positions_helper(all_players_all_partial_placements, reference_player):
    all_partial_placements = all_players_all_partial_placements[reference_player]
    if all_partial_placements is None:
        return None, AllFurthestPartialPlacements()

    all_furthest_partial_placements = AllFurthestPartialPlacements()

    all_possible_placements = []

    for partial_placements in all_partial_placements:
        if partial_placements.player != reference_player:
            raise RuntimeError()

        find_all_player_positions_helper2(all_possible_placements, all_furthest_partial_placements, all_players_all_partial_placements, 0, partial_placements)

    return all_possible_placements, all_furthest_partial_placements

num_calls = 0

def find_all_player_positions_helper2(all_possible_placements, all_furthest_partial_placements, all_players_all_partial_placements, cur_player, base_partial_placements):
    #for i in range(cur_player, len(all_players_all_partial_placements)):
    #global num_calls
    #num_calls += 1
    #print(f"num_calls: {num_calls}")

    if cur_player < len(all_players_all_partial_placements):
        all_partial_placements = all_players_all_partial_placements[cur_player]
        if all_partial_placements is None or cur_player == base_partial_placements.player:
            find_all_player_positions_helper2(all_possible_placements, all_furthest_partial_placements, all_players_all_partial_placements, cur_player + 1, base_partial_placements)
        else:
            for partial_placements in all_partial_placements:
                new_all_players_possible_placements = {}
                #available_placements = set(range(1, len(all_players_all_partial_placements) + 1)):
                placement_slices_tally = collections.defaultdict(int)
                merge_not_possible = False
        
                for player, player_possible_placements in base_partial_placements.all_players_possible_placements.items():
                    try:
                        new_player_possible_placements = player_possible_placements & partial_placements.all_players_possible_placements[player]
                    except TypeError as e:
                        print(f"partial_placements.all_players_possible_placements: {partial_placements.all_players_possible_placements}")
                        raise RuntimeError(e)

                    #print(f"type(placement_slices_tally).__name__: {type(placement_slices_tally).__name__}")
                    placement_slices_tally[new_player_possible_placements] += 1
                    if placement_slices_tally[new_player_possible_placements] > len(new_player_possible_placements):
                        merge_not_possible = True
                        break
        
                    new_all_players_possible_placements[player] = new_player_possible_placements
        
                if merge_not_possible:
                    num_single_slices = 0

                    for player, player_possible_placements in base_partial_placements.all_players_possible_placements.items():
                        if len(player_possible_placements) == 1:
                            num_single_slices += 1

                    if num_single_slices > all_furthest_partial_placements.num_single_slices:
                        all_furthest_partial_placements.values = [base_partial_placements]
                    elif num_single_slices == all_furthest_partial_placements.num_single_slices:
                        all_furthest_partial_placements.values.append(base_partial_placements)

                    continue
        
                new_base_partial_placements = PartialPlacements.from_all_players_possible_placements(base_partial_placements.player, new_all_players_possible_placements)

                find_all_player_positions_helper2(all_possible_placements, all_furthest_partial_placements, all_players_all_partial_placements, cur_player + 1, new_base_partial_placements)
    else:
        all_possible_placements.append(base_partial_placements)
            

def find_all_player_positions_sample():
    initial_vrs = [
        9297, # 0
        9261, # 1
        9510, # 2
        7243, # 3
        8901, # 4
        8356, # 5
        8192, # 6
        9999, # 7
        9417, # 8
        7258, # 9
        9796, # 10
        9999  # 11
    ]

    expected_vrs = [
        9375, # 0
        9288, # 1 # 9256
        9549, # 2
        7169, # 3
        9030, # 4
        8547, # 5
        8194, # 6
        9811, # 7
        9320, # 8
        7410, # 9
        9731, # 10
        9837  # 11
    ]

    find_all_player_positions(initial_vrs, expected_vrs)

def find_all_player_positions_missing_vrs_sample():
    initial_vrs = [
        7631, # 0
        9966, # 1
        8870, # 2
        6593, # 3
        8148, # 4
        6411, # 5
        9594, # 6
        9306, # 7
        9999, # 8
        8294, # 9
        5684, # 10
        4939  # 11
    ]

    expected_vrs = [
        7550, # 0
        9958, # 1
        -1, # 2
        6637, # 3
        -1, # 4
        -1, # 5
        9628, # 6
        9377, # 7
        9999, # 8
        8296, # 9
        5645, # 10
        -1  # 11
    ]

    find_all_player_positions(initial_vrs, expected_vrs)

def find_player_pos_sample():
    initial_vrs = [
        9297, # 0
        9261, # 1
        9510, # 2
        7243, # 3
        8901, # 4
        8356, # 5
        8192, # 6
        9999, # 7
        9417, # 8
        7258, # 9
        9796, # 10
        9999  # 11
    ]

    player = 9
    expected_vr = 7410
    output_all_partial_placements(find_player_pos(initial_vrs, player, expected_vr), player)

def find_all_player_positions_sample2():
    initial_vrs = [
        9218, # 0
        8905, # 1
        9766, # 2
        7302, # 3
        9352, # 4
        8562, # 5
        8208, # 6
        9964, # 7
        9476, # 8
        7668, # 9
        9470, # 10
        9552  # 11
    ]

    expected_vrs = [
        9155, # 0
        8907, # 1
        9814, # 2
        8457, # 3
        9245, # 4
        8540, # 5
        8175, # 6
        9978, # 7
        9285, # 8
        8029, # 9
        9302, # 10
        9721  # 11
    ]

    find_all_player_positions(initial_vrs, expected_vrs)

def main():
    MODE = 5
    if MODE == 0:
        test_all_perms_len()
    elif MODE == 1:
        gen_all_perms_12p()
    elif MODE == 2:
        find_player_pos_sample()
    elif MODE == 3:
        find_all_player_positions_sample()
    elif MODE == 4:
        find_all_player_positions_missing_vrs_sample()
    elif MODE == 5:
        find_all_player_positions_sample2()
    else:
        print("No mode selected!")

if __name__ == "__main__":
    main()
