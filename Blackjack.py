import numpy as np
import numba
import time

class Shoe():
    def __init__(self, num_decks, penetration):
        self.num_decks = num_decks
        self.penetration = penetration
        self.count_values = np.array([0, 0, 1, 1, 1, 1, 1, 0, 0, 0, -1, -1, -1, -1, -1], dtype=np.int8)
        self.reset()

    def reset(self):
        ranks = np.array([11, 10, 10, 10, 10, 9, 8, 7, 6, 5, 4, 3, 2], dtype=np.int8)
        one_deck = np.repeat(ranks, 4)
        self.shoe = np.tile(one_deck, self.num_decks)
        np.random.shuffle(self.shoe)
        self.index = 0
        self.running_count = 0
    
    def draw(self):
        if self.index >= self.penetration * 52 - 1:
            self.reset()

        card = self.shoe[self.index]
        self.index += 1
        self.running_count += self.count_values[card]

        return card

    def get_true_count(self):
        decksLeft = np.round(self.num_decks - self.index / 52)
        if decksLeft == 0:
            return self.running_count
        return self.running_count / decksLeft
    
class Hand():
    def __init__(self, card):
        self.is_first_move = True
        self.is_duplicate = False
        self.can_split = True
        self.aces_split = False
        self.type = 'hard'
        self.hand = np.zeros(12, dtype=np.int8)
        self.hand[0] = card
        self.card_names = np.array(['0', '0', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'A'], dtype='<U1')
        if (card == 11):
            self.type = 'soft'
        self.value = card
        self.num_cards = 1

    def add_card(self, card):
        self.hand[self.num_cards] = card
        self.num_cards += 1

        if self.num_cards == 2 and self.hand[0] == self.hand[1]:
            self.is_duplicate = True
        if self.num_cards > 2:
            self.is_duplicate = False

        self.value += card

        if self.value > 21 and self.type == 'soft':
            self.value -= 10
            self.type = 'hard'
        if card == 11:
            self.type = 'soft'
        if self.value > 21 and self.type == 'soft':
            self.value -= 10
            self.type = 'hard'
        if self.num_cards > 2:
            self.is_first_move = False

    def split(self):
        if self.hand[0] == 11:
            self.aces_split = True
        self.can_split = False
        self.value = self.hand[0]
        self.hand[1] = 0
        self.num_cards -= 1
        return self.hand[0]

    def print_hand(self):
        for card in self.hand:
            if card != 0:
                print(self.card_names[card], end='')
        print("  (" + str(self.value) + ")")

    
class BlackjackGame():
    def __init__(self, num_decks, penetration, num_splits_allowed):
        self.shoe = Shoe(num_decks, penetration)
        self.num_splits_allowed = num_splits_allowed
        self.t = 0

    def start_hand(self):
        self.terminated_statuses = [False]

        start = time.perf_counter()
        self.player_hands = [Hand(self.shoe.draw())] #THESE 4 LINES OPTIMIZE
        self.dealer_hand = Hand(self.shoe.draw())
        self.player_hands[0].add_card(self.shoe.draw())
        self.dealer_down_card = self.shoe.draw()
        self.t += time.perf_counter() - start

        if self.player_hands[0].value == 21 or self.dealer_hand.value + self.dealer_down_card == 21:
            self.terminated_statuses[0] = True
            self.dealer_hand.add_card(self.dealer_down_card)

        return (self.player_hands, self.dealer_hand)

    def take_turn(self, action, hand_ind):
        if len(self.player_hands) == 0:
            raise ValueError('Hand has not been started yet')
        if self.terminated_statuses[hand_ind]:
            raise ValueError('Turn is already over')

        if action == ACTION_HIT:
            self.player_hands[hand_ind].add_card(self.shoe.draw())

        elif action == ACTION_DOUBLE:
            if self.player_hands[hand_ind].is_first_move:
                self.terminated_statuses[hand_ind] = True
            self.player_hands[hand_ind].add_card(self.shoe.draw())  

        elif action == ACTION_DOUBLE_OR_STAND:
            if self.player_hands[hand_ind].is_first_move:
                self.player_hands[hand_ind].add_card(self.shoe.draw())
            self.terminated_statuses[hand_ind] = True

        elif action == ACTION_SPLIT:
            if len(self.player_hands) == self.num_splits_allowed + 1:
                raise ValueError('Maximum number of splits already reached')
            
            self.terminated_statuses.append(False)
            
            if self.player_hands[hand_ind].value == 12 and self.player_hands[hand_ind].type == 'soft':
                self.terminated_statuses[hand_ind] = True
                self.terminated_statuses[-1] = True
            
            self.player_hands.append(Hand(self.player_hands[hand_ind].split()))
            self.player_hands[hand_ind].add_card(self.shoe.draw())
            self.player_hands[-1].add_card(self.shoe.draw()) 

            if self.player_hands[-1].value >= 21:
                self.terminated_statuses[-1] = True

        elif action == ACTION_STAND:
            self.terminated_statuses[hand_ind] = True

        if self.player_hands[hand_ind].value >= 21:
            self.terminated_statuses[hand_ind] = True

        if all(self.terminated_statuses):
            self.terminate_hand()
        
        return (self.player_hands, self.dealer_hand)
    
    def terminate_hand(self):
        self.dealer_hand.add_card(self.dealer_down_card)
        while self.dealer_hand.value < 17:
            self.dealer_hand.add_card(self.shoe.draw())


class BlackjackSimulator():
    def __init__(self, num_decks, penetration, num_splits_allowed):
        self.game = BlackjackGame(num_decks, penetration, num_splits_allowed)
        self.num_splits_allowed = num_splits_allowed

    def simulate_EV(self, start_bankroll, min_bet_size, play_deviations, num_hands_to_play, spread=None, flooring=False, print_hands=False):
        if spread == None:
            spread = [1]

        bankroll = start_bankroll

        for _ in range(num_hands_to_play):
            true_count = self.game.shoe.get_true_count()
            rounded_true_count = int(np.floor(true_count)) if flooring else int(np.round(true_count))

            if rounded_true_count >= len(spread):
                curr_bet_sizes = [min_bet_size * spread[-1]]
            elif rounded_true_count < 0:
                curr_bet_sizes = [min_bet_size * spread[0]]
            else:
                curr_bet_sizes = [min_bet_size * spread[rounded_true_count]]

            player_hands, dealer_hand = self.game.start_hand()  #THIS METHOD TAKES HALF THE EXECUTION TIME

            if player_hands[0].value == 21 and dealer_hand.value != 21:
                bankroll += curr_bet_sizes[0] * 1.5
                if print_hands: 
                    player_hands[0].print_hand()
                    print(curr_bet_sizes[0]*1.5)
                    dealer_hand.print_hand()
                    print()
            else:
                while not all(self.game.terminated_statuses):
                    for i in range(len(player_hands)):
                        if not self.game.terminated_statuses[i]:
                            max_splits_reached = len(player_hands) == self.num_splits_allowed + 1
                            action = calculate_move_logic(dealer_hand, player_hands[i], max_splits_reached=max_splits_reached,
                                                           play_deviations=play_deviations, true_count=rounded_true_count, running_count=self.game.shoe.running_count)
                            #action = calculate_move_LUT2(player_hands[i].value, dealer_hand.value, player_hands[i].type == 'soft', player_hands[i].is_duplicate,
                            #                             player_hands[i].hand[0].value, player_hands[i].can_split, max_splits_reached, rounded_true_count, self.game.shoe.running_count)
                            if action == ACTION_SPLIT:
                                curr_bet_sizes.append(curr_bet_sizes[i])
                            if (action == ACTION_DOUBLE or action == ACTION_DOUBLE_OR_STAND) and player_hands[i].is_first_move:
                                curr_bet_sizes[i] *= 2
                            self.game.take_turn(action, i) #1/4 of run time

                for i in range(len(player_hands)):
                    if print_hands: player_hands[i].print_hand()
                    if player_hands[i].value > 21:
                        bankroll -= curr_bet_sizes[i]
                        if print_hands: print(-curr_bet_sizes[i])
                    elif dealer_hand.value > 21:
                        bankroll += curr_bet_sizes[i]
                        if print_hands: print(curr_bet_sizes[i])
                    elif player_hands[i].value > dealer_hand.value:
                        bankroll += curr_bet_sizes[i]
                        if print_hands: print(curr_bet_sizes[i])
                    elif player_hands[i].value < dealer_hand.value:
                        bankroll -= curr_bet_sizes[i]
                        if print_hands: print(-curr_bet_sizes[i])
                    else: 
                        if print_hands: print(0)
                if print_hands:
                    dealer_hand.print_hand()
                    print()

        print(self.game.t)
        simulated_profit = bankroll - start_bankroll
        player_edge_percentage = simulated_profit / num_hands_to_play / min_bet_size * 100
        return simulated_profit, player_edge_percentage
    
#Additional Considerations
#1   Don't let dealer draw more cards if the player busts or figure out how that works
#2   Play out hand if dealer has Blackjack but is showing a 10
#3   Add insurance implemenation

ACTION_HIT, ACTION_STAND, ACTION_DOUBLE, ACTION_SPLIT, ACTION_DOUBLE_OR_STAND = range(5)

split_base_action = np.full((12, 12), 0, dtype=np.int8)
split_dev_count = np.full((12, 12), 9999, dtype=np.int16)
split_alt_action  = np.empty((12, 12), dtype=np.int8)

for i in range(2, 12):
    split_base_action[11][i] = ACTION_SPLIT
    split_base_action[8][i] = ACTION_SPLIT

    if i <= 9 and i != 7:
        split_base_action[9][i] = ACTION_SPLIT
    if i <= 7:
        split_base_action[7][i] = ACTION_SPLIT
        split_base_action[3][i] = ACTION_SPLIT
        split_base_action[2][i] = ACTION_SPLIT
    if i <= 6:
        split_base_action[6][i] = ACTION_SPLIT
split_dev_count[10][6] = 4
split_alt_action[10][6] = ACTION_SPLIT
split_dev_count[10][5] = 5
split_alt_action[10][5] = ACTION_SPLIT
split_dev_count[10][4] = 6
split_alt_action[10][4] = ACTION_SPLIT
split_base_action[4][6] = ACTION_SPLIT
split_base_action[4][5] = ACTION_SPLIT

soft_base_action = np.full((21, 12), ACTION_HIT, dtype=np.int8)
soft_dev_count = np.full((21, 12), 9999, dtype=np.int16)
soft_alt_action  = np.empty((21, 12), dtype=np.int8)

for i in range(2, 12):
    soft_base_action[20][i] = ACTION_STAND
    soft_base_action[19][i] = ACTION_STAND
    if i <= 6:
        soft_base_action[18][i] = ACTION_DOUBLE_OR_STAND
    if i == 7 or i == 8:
        soft_base_action[18][i] = ACTION_STAND
        soft_base_action[18][i] = ACTION_STAND
    if i <= 6 and i >= 3:
        soft_base_action[17][i] = ACTION_DOUBLE
    if i <= 6 and i >= 4:
        soft_base_action[16][i] = ACTION_DOUBLE
        soft_base_action[15][i] = ACTION_DOUBLE
    if i <= 6 and i >= 5:
        soft_base_action[14][i] = ACTION_DOUBLE
        soft_base_action[13][i] = ACTION_DOUBLE
soft_dev_count[19][6] = 1
soft_alt_action[19][6] = ACTION_DOUBLE_OR_STAND
soft_dev_count[19][5] = 1
soft_alt_action[19][5] = ACTION_DOUBLE_OR_STAND
soft_dev_count[19][4] = 3
soft_alt_action[19][4] = ACTION_DOUBLE_OR_STAND
soft_dev_count[17][2] = 1
soft_alt_action[17][2] = ACTION_DOUBLE

hard_base_action = np.full((21, 12), ACTION_HIT, dtype=np.int8)
hard_dev_count = np.full((21, 12), 9999, dtype=np.int16)
hard_alt_action  = np.empty((21, 12), dtype=np.int8)
hard_deviation_type   = np.zeros((22, 12), dtype=np.int8)

for i in range(2, 12):
    hard_base_action[20][i]= ACTION_STAND
    hard_base_action[19][i] = ACTION_STAND
    hard_base_action[18][i] = ACTION_STAND
    hard_base_action[17][i] = ACTION_STAND
    if i <= 6:
        hard_base_action[16][i] = ACTION_STAND
        hard_base_action[15][i] = ACTION_STAND
        hard_base_action[14][i] = ACTION_STAND
        hard_base_action[13][i] = ACTION_STAND
        if i >= 4:
            hard_base_action[12][i] = ACTION_STAND
    if i <= 10:
        hard_base_action[11][i] = ACTION_DOUBLE
    if i <= 9:
        hard_base_action[10][i] = ACTION_DOUBLE
    if i <= 6 and i >= 3:
        hard_base_action[9][i] = ACTION_DOUBLE
hard_dev_count[16][10] = 0
hard_alt_action[16][10] = ACTION_STAND
hard_deviation_type[16][10] = 3
hard_dev_count[16][9] = 4
hard_alt_action[16][9] = ACTION_STAND
hard_deviation_type[16][9] = 1
hard_dev_count[15][10] = 4
hard_alt_action[15][10] = ACTION_STAND
hard_deviation_type[15][10] = 1
hard_dev_count[13][2] = -1
hard_alt_action[13][2] = ACTION_HIT
hard_deviation_type[13][2] = 2
hard_dev_count[12][2] = 3
hard_alt_action[12][2] = ACTION_STAND
hard_deviation_type[12][2] = 1
hard_dev_count[12][3] = 2
hard_alt_action[12][3] = ACTION_STAND
hard_deviation_type[12][3] = 1
hard_dev_count[12][4] = 0
hard_alt_action[12][4] = ACTION_HIT
hard_deviation_type[12][4] = 4
hard_dev_count[9][2] = 1
hard_alt_action[9][2] = ACTION_DOUBLE
hard_deviation_type[9][2] = 1
hard_dev_count[9][7] = 3
hard_alt_action[9][7] = ACTION_DOUBLE
hard_deviation_type[9][7] = 1
hard_dev_count[8][6] = 2
hard_alt_action[8][6] = ACTION_DOUBLE
hard_deviation_type[8][6] = 1
hard_dev_count[11][11] = 1
hard_alt_action[11][11] = ACTION_DOUBLE
hard_deviation_type[11][11] = 1
hard_dev_count[10][11] = 4
hard_alt_action[10][11] = ACTION_DOUBLE
hard_deviation_type[10][11] = 1
hard_dev_count[10][10] = 4
hard_alt_action[10][10] = ACTION_DOUBLE
hard_deviation_type[10][10] = 1


#@numba.njit
def calculate_move_LUT(dealer_hand: Hand, player_hand: Hand, max_splits_reached=False, play_deviations=False, true_count=0, running_count=0):
    player_value = player_hand.value
    up_card = dealer_hand.value

    if player_hand.is_duplicate and not max_splits_reached and player_hand.can_split:
        rank = player_hand.hand[0].value
        if play_deviations and true_count >= split_dev_count[rank][up_card]:
            return split_alt_action[rank][up_card]
        elif split_base_action[rank][up_card] == ACTION_SPLIT:
            return ACTION_SPLIT
    if player_hand.type == 'soft':
        if play_deviations and true_count >= soft_dev_count[player_value][up_card]:
            return soft_alt_action[player_value][up_card]
        else:
            return soft_base_action[player_value][up_card]
    if player_hand.type == 'hard':
        if play_deviations and hard_deviation_type[player_value][up_card] != 0:
            dev_type = hard_deviation_type[player_value][up_card]
            dev_count = hard_dev_count[player_value][up_card]
            if (dev_type == 1 and true_count >= dev_count) or (dev_type == 2 and true_count <= dev_count) or (dev_type == 3 and running_count >= dev_count) or (dev_type == 4 and running_count <= dev_count):
                return hard_alt_action[player_value][up_card]    
        else:
            return hard_base_action[player_value][up_card]

    return None

@numba.njit
def calculate_move_LUT2(player_total, dealer_up, is_soft, is_pair, rank, can_split, max_splits_reached, true_count, running_count):
    if is_pair and can_split and not max_splits_reached:
        base = split_base_action[rank][dealer_up]
        dev  = split_dev_count[rank][dealer_up]
        alt  = split_alt_action[rank][dealer_up]
        if true_count >= dev:
            return alt
        return base

    if is_soft:
        base = soft_base_action[player_total][dealer_up]
        dev  = soft_dev_count[player_total][dealer_up]
        alt  = soft_alt_action[player_total][dealer_up]
        if true_count >= dev:
            return alt
        return base

    # hard hands
    base = hard_base_action[player_total][dealer_up]
    dev_type = hard_deviation_type[player_total][dealer_up]
    dev_count = hard_dev_count[player_total][dealer_up]
    alt = hard_alt_action[player_total][dealer_up]

    if dev_type == 1 and true_count >= dev_count:
        return alt
    if dev_type == 2 and true_count <= dev_count:
        return alt
    if dev_type == 3 and running_count >= dev_count:
        return alt
    if dev_type == 4 and running_count <= dev_count:
        return alt

    return base


def calculate_move_logic(dealer_hand: Hand, player_hand: Hand, max_splits_reached=False, play_deviations=False, true_count=0, running_count=0):

    #Value of player hand and dealer upcard
    player_value = player_hand.value
    up_card = dealer_hand.value

    #Auto stands after splitting aces
    if player_hand.aces_split:
        return ACTION_STAND
    
    #Plays card counting deviations if enabled
    if play_deviations:
        if player_hand.is_duplicate and player_hand.can_split and player_value == 20 and not max_splits_reached:
            if up_card == 6 and true_count >= 4 or up_card == 5 and true_count >= 5 or up_card == 4 and true_count >= 6:
                return ACTION_SPLIT
            
        if player_hand.type == 'soft':
            if player_value == 19 and player_hand.is_first_move:
                if up_card == 4 and true_count >= 3 or up_card == 5 and true_count >= 1 or up_card == 6 and true_count >= 1:
                    return ACTION_DOUBLE_OR_STAND
            
            if player_value == 17:
                if up_card == 2 and true_count >= 1:
                    return ACTION_DOUBLE
                
        if player_hand.type == 'hard':
            if player_value == 16:
                if up_card == 9 and true_count >= 4 or up_card == 10 and running_count > 0:
                    return ACTION_STAND
            
            if player_value == 15:
                if up_card == 10 and true_count >= 4:
                    return ACTION_STAND
            
            if player_value == 13:
                if up_card == 2 and true_count <= -1:
                    return ACTION_HIT
    
            if player_value == 12:
                if up_card == 2 and true_count >= 3 or up_card == 3 and true_count >= 2:
                    return ACTION_STAND
                if up_card == 4 and running_count < 0:
                    return ACTION_HIT
                
            if player_value == 11:
                if up_card == 11 and true_count >= 1:
                    return ACTION_DOUBLE
                
            if player_value == 10:
                if (up_card == 10 or up_card == 11) and true_count >= 4:
                    return ACTION_DOUBLE
                
            if player_value == 9:
                if up_card == 2 and true_count >= 1 or up_card == 7 and true_count >= 3:
                    return ACTION_DOUBLE
                
            if player_value == 8:
                if up_card == 6 and true_count >= 2:
                    return ACTION_DOUBLE
                
    #Basic strategy for doubles
    if player_hand.is_duplicate and player_hand.can_split and not max_splits_reached:
        if player_value == 12 and player_hand.type == 'soft':
            return ACTION_SPLIT
        
        if player_value == 18:
            if up_card <= 9 and up_card != 7:
                return ACTION_SPLIT
            
        if player_value == 16:
            return ACTION_SPLIT
        
        if player_value == 14:
            if up_card <= 7:
                return ACTION_SPLIT
            
        if player_value == 12:
            if up_card <= 6:
                return ACTION_SPLIT
            
        if player_value == 8:
            if up_card == 6 or up_card == 5:
                return ACTION_SPLIT
            
        if player_value == 6 or player_value == 4:
            if up_card <= 7:
                return ACTION_SPLIT
            
    #Basic strategy for soft totals
    if player_hand.type == 'soft':
        if player_value >= 19:
            # if up_card == 6 and player_value == 19:   Could try this variant double S19 vs dealer 6
            #     return ACTION_DOUBLE
            return ACTION_STAND
        
        if player_value == 18:
            if up_card <= 6:
                return ACTION_DOUBLE_OR_STAND
            if up_card == 7 or up_card == 8:
                return ACTION_STAND
            return ACTION_HIT
        
        if player_value == 17:
            if up_card <= 6 and up_card >= 3:
                return ACTION_DOUBLE
            return ACTION_HIT
        
        if player_value == 16 or player_value == 15:
            if up_card <= 6 and up_card >= 4:
                return ACTION_DOUBLE
            return ACTION_HIT
        
        if player_value == 14 or player_value == 13:
            if up_card == 5 or up_card == 6:
                return ACTION_DOUBLE
            return ACTION_HIT
        
        if player_value == 12:
            return ACTION_HIT
        
    #Basic strategy for hard totals
    if player_hand.type == 'hard':
        if player_value >= 17:
            return ACTION_STAND
        
        if player_value >= 13 and player_value <= 16:
            if up_card <= 6:
                return ACTION_STAND
            return ACTION_HIT  

        if player_value == 12:
            if up_card >= 4 and up_card <= 6:
                return ACTION_STAND
            return ACTION_HIT  
        
        if player_value == 11:
            if up_card <= 10:
                return ACTION_DOUBLE
            return ACTION_HIT
        
        if player_value == 10:
            if up_card <= 9:
                return ACTION_DOUBLE
            return ACTION_HIT
        
        if player_value == 9:
            if up_card <= 6 and up_card >= 3:
                return ACTION_DOUBLE
            return ACTION_HIT
        
        if player_value <= 8:
            return ACTION_HIT
        
        raise ValueError('Move Calculator did not account for this situation')