package com.summer.stockproject.login.service;

import com.summer.stockproject.login.Entity.User;
import com.summer.stockproject.login.dao.UserRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;

import java.util.Optional;

@Service
public class MyUserDetailsService implements UserDetailsService {
    @Autowired
    private UserRepository userRepository;

    @Override
    public UserDetails loadUserByUsername(String Id) throws UsernameNotFoundException {
        User user = userRepository.getReferenceById(Id);
        MyUserDetails userDetails = new MyUserDetails(user);

        return userDetails;
    }
}
