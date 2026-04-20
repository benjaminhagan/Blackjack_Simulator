import numpy as np

class Card():
    def __init__(self, name, value):
        self.name = name
        self.value = value

class Shoe():
    def __init__(self, num_decks, penetration):
        self.num_decks = num_decks
        self.penetration = penetration
        self.running_count = 0
        self.shoe = []
        self.discard = []

        for _ in range(num_decks * 4):
            self.shoe.append(Card(name='A', value=11))
            self.shoe.append(Card(name='K', value=10))
            self.shoe.append(Card(name='Q', value=10))
            self.shoe.append(Card(name='J', value=10))
            self.shoe.append(Card(name='T', value=10))
            self.shoe.append(Card(name='9', value=9))
            self.shoe.append(Card(name='8', value=8))
            self.shoe.append(Card(name='7', value=7))
            self.shoe.append(Card(name='6', value=6))
            self.shoe.append(Card(name='5', value=5))
            self.shoe.append(Card(name='4', value=4))
            self.shoe.append(Card(name='3', value=3))
            self.shoe.append(Card(name='2', value=2))

    def draw(self):
        if len(self.shoe) <= (self.num_decks-self.penetration)*52 or len(self.shoe) == 0:
            self.shuffle()

        new_card = self.shoe.pop(np.random.randint(0, len(self.shoe)))
        self.discard.append(new_card)

        if new_card.value > 9:
            self.running_count -= 1
        elif new_card.value < 7:
            self.running_count += 1

        return new_card

    def shuffle(self):
        while self.discard:
            self.shoe.append(self.discard.pop())
        
        self.running_count = 0

    def get_true_count(self):
        decksLeft = np.round(len(self.shoe) / 52.0)
        if decksLeft == 0:
            return self.running_count
        return self.running_count / decksLeft
    
class Hand():
    def __init__(self, card):
        self.is_first_move = True
        self.is_duplicate = False
        self.aces_split = False
        self.type = 'hard'
        self.hand = [card]
        if (card.name == 'A'):
            self.type = 'soft'
        self.value = card.value

    def add_card(self, card: Card):
        self.hand.append(card)

        if len(self.hand) == 2 and self.hand[0].value == self.hand[1].value:
            self.is_duplicate = True
        if len(self.hand) > 2:
            self.is_duplicate = False

        self.value += card.value

        if self.value > 21 and self.type == 'soft':
            self.value -= 10
            self.type = 'hard'
        if card.value == 11:
            self.type = 'soft'
        if self.value > 21 and self.type == 'soft':
            self.value -= 10
            self.type = 'hard'
        if len(self.hand) > 2:
            self.is_first_move = False

    def split(self):
        if self.hand[0].value == 11:
            self.aces_split = True
        self.is_duplicate = False
        self.value = self.hand[0].value
        return self.hand.pop(0)

    def print_hand(self):
        for card in self.hand:
            print(card.name, end='')
        print("  (" + str(self.value) + ")")

    
class BlackjackGame():
    def __init__(self, num_decks, penetration, num_splits_allowed):
        self.shoe = Shoe(num_decks, penetration)
        self.num_splits_allowed = num_splits_allowed

    def start_hand(self):
        self.dealer_blackjack = False
        self.player_blackjack = False
        self.terminated_statuses = [False]
        self.player_hands = [Hand(self.shoe.draw())] #THESE 4 LINES OPTIMIZE
        self.dealer_hand = Hand(self.shoe.draw())
        self.player_hands[0].add_card(self.shoe.draw())
        self.dealer_down_card = self.shoe.draw()
        if self.dealer_hand.value == 11 and self.dealer_down_card.value == 10:
        #if self.dealer_hand.value + self.dealer_down_card.value == 21:
           self.dealer_blackjack = True
        if self.player_hands[0].value == 21:
            self.player_blackjack = True

        return (self.player_hands, self.dealer_hand)

    def take_turn(self, action, hand_ind):
        if len(self.player_hands) == 0:
            raise ValueError('Hand has not been started yet')
        if self.terminated_statuses[hand_ind]:
            raise ValueError('Turn is already over')

        if self.dealer_blackjack:
            pass

        elif action == ACTION_HIT:
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

        if self.player_hands[hand_ind].value >= 21 or self.dealer_blackjack:
            self.terminated_statuses[hand_ind] = True

        if all(self.terminated_statuses):
            self.terminate_hand()
        
        return (self.player_hands, self.dealer_hand)
    
    def terminate_hand(self):
        self.dealer_hand.add_card(self.dealer_down_card)
        if not self.player_blackjack:
            while self.dealer_hand.value < 17:
                self.dealer_hand.add_card(self.shoe.draw())


class BlackjackSimulator():
    def __init__(self, num_decks, penetration, num_splits_allowed):
        self.game = BlackjackGame(num_decks, penetration, num_splits_allowed)
        self.num_splits_allowed = num_splits_allowed

    def simulate_EV(self, min_bet_size, play_deviations, num_hands_to_play, spread=None, flooring=False, print_hands=False):
        if spread == None:
            spread = [1]

        bankroll = 0

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
            
            insurance_available = dealer_hand.value == 11
            insurance_win = 0
            # if self.game.dealer_blackjack:
            #     print_hands = True

            while not all(self.game.terminated_statuses):
                for i in range(len(player_hands)):
                    if not self.game.terminated_statuses[i]:

                        max_splits_reached = len(player_hands) == self.num_splits_allowed + 1
                        action = calculate_move_logic(dealer_hand, player_hands[i], insurance_available, max_splits_reached=max_splits_reached,
                                                        play_deviations=play_deviations, true_count=rounded_true_count, running_count=self.game.shoe.running_count)
                        
                        if action != ACTION_INSURANCE and self.game.dealer_blackjack:
                            pass
                        elif action == ACTION_SPLIT:
                            curr_bet_sizes.append(curr_bet_sizes[i])
                        elif (action == ACTION_DOUBLE or action == ACTION_DOUBLE_OR_STAND) and player_hands[i].is_first_move:
                            curr_bet_sizes[i] *= 2
                        elif action == ACTION_INSURANCE:
                            insurance_win -= curr_bet_sizes[i] / 2
                            if dealer_hand.value + self.game.dealer_down_card.value == 21:
                                insurance_win += curr_bet_sizes[i] / 2 * 3
                        
                        insurance_available = False

                        self.game.take_turn(action, i) #1/4 of run time

            if player_hands[0].value == 21 and len(player_hands) == 1 and player_hands[0].is_first_move and dealer_hand.value != 21:
                bankroll += curr_bet_sizes[0] * 1.5
                if print_hands: 
                    player_hands[0].print_hand()
                    print(curr_bet_sizes[0] * 1.5)
                    dealer_hand.print_hand()
                    print()
            else:
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

            bankroll += insurance_win
            if print_hands and insurance_win != 0: print(f'Insurance Win: {insurance_win}')

        player_edge_percentage = bankroll / num_hands_to_play / min_bet_size * 100
        return player_edge_percentage
    
    def simulate_risk_of_ruin(self, start_bankroll, sl, tp, min_bet_size, play_deviations, trials_to_run, spread=None, flooring=False, print_hands=False):
        if spread == None:
            spread = [1]

        wins = 0
        losses = 0

        for _ in range(trials_to_run):
            bankroll = start_bankroll
            while bankroll >= sl and bankroll <= tp:
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

            if bankroll >= tp:
                wins += 1
            elif bankroll <= 0:
                losses += 1
            else:
                raise ValueError('Something went wrong')

        risk_of_ruin = losses / trials_to_run * 100
        return risk_of_ruin
    
#Additional Considerations
#1   Don't let dealer draw more cards if the player busts or figure out how that works
#2   Play out hand if dealer has Blackjack but is showing a 10
#3   Add insurance implemenation
#4 MAKE SURE DONT TAKE INSURANCE AFTER SPLIT

ACTION_HIT, ACTION_STAND, ACTION_DOUBLE, ACTION_SPLIT, ACTION_DOUBLE_OR_STAND, ACTION_INSURANCE = range(6)


def calculate_move_logic(dealer_hand: Hand, player_hand: Hand, insurance_available, max_splits_reached=False, play_deviations=False, true_count=0, running_count=0):

    #Value of player hand and dealer upcard
    player_value = player_hand.value
    up_card = dealer_hand.value

    #Auto stands after splitting aces
    if player_hand.aces_split:
        return ACTION_STAND
    
    #Plays card counting deviations if enabled
    if play_deviations:

        if up_card == 11 and true_count >= 3 and insurance_available and player_hand.is_first_move:
            return ACTION_INSURANCE

        if player_hand.is_duplicate and player_value == 20 and not max_splits_reached:
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
    if player_hand.is_duplicate and not max_splits_reached:
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