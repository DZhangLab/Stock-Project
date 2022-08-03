package com.summer.stockproject.login.service;

import com.summer.stockproject.login.Entity.User;
import org.springframework.stereotype.Service;

@Service
public interface UserService {
    public User getReferenceById(String email);
    public void save(User user);

}
